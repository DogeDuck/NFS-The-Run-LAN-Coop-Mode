"""Offline snapshot validation and deduplication. No Windows/process APIs."""
import argparse
import json
from pathlib import Path
import struct
from teleport_probe_adapter import REQUIRED_STATS_BYTES, RING_OFFSET, STRIDE, SLOTS, FIELDS, summarize_events


def stable_events(first, second):
    """Only accept slots byte-identical across two snapshots, committed and current.

    This detects observed torn writes, not arbitrary ABA/concurrent writer safety.
    Counter wrap is deliberately rejected; restart the diagnostic before 2^32 calls.
    """
    if min(len(first), len(second)) < REQUIRED_STATS_BYTES:
        raise ValueError('Truncated snapshot pair')
    head_a, head_b = struct.unpack_from('<I', first)[0], struct.unpack_from('<I', second)[0]
    if struct.unpack_from('<I', first, 12)[0] or struct.unpack_from('<I', second, 12)[0]:
        raise ValueError('Probe counter wrapped; start a new capture epoch')
    if head_b < head_a:
        raise ValueError('Counter reset/wrap; start a new capture epoch')
    events = []
    unstable = 0
    for slot in range(SLOTS):
        start = RING_OFFSET + slot * STRIDE
        a, b = first[start:start + STRIDE], second[start:start + STRIDE]
        if a != b:
            unstable += 1
            continue
        values = struct.unpack('<8I', b)
        seq = values[0]
        if not seq or seq != values[-1]:
            continue
        if seq > head_a or head_b - seq >= SLOTS or (seq - 1) % SLOTS != slot:
            continue
        events.append(dict(zip(FIELDS, values)))
    return dict(head=head_b, unstable_slots=unstable,
                contention_drops=struct.unpack_from('<I', second, 8)[0],
                events=sorted(events, key=lambda event: event['sequence']))


class RingTracker:
    def __init__(self):
        self.head = 0
        self.seen = set()
        self.expired_through = 0
        self.unobserved_expired = 0

    def consume(self, first, second):
        pair = stable_events(first, second)
        head = pair['head']
        if head < self.head:
            raise ValueError('Counter reset; new tracker required')
        new = [event for event in pair['events'] if event['sequence'] not in self.seen]
        self.seen.update(event['sequence'] for event in new)
        # Retain out-of-order commits until they leave the ring's recoverable window.
        cutoff = max(0, head - SLOTS)
        total_expired = cutoff - self.expired_through
        recovered = sum(self.expired_through < seq <= cutoff for seq in self.seen)
        self.unobserved_expired += total_expired - recovered
        self.seen = {seq for seq in self.seen if seq > cutoff}
        self.expired_through = cutoff
        self.head = head
        return dict(new_events=new, head=head, unstable_slots=pair['unstable_slots'],
                    contention_drops=pair['contention_drops'],
                    unobserved_expired=self.unobserved_expired,
                    pending_in_window=min(head, SLOTS) - len(self.seen))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path, help='First saved raw stats snapshot')
    parser.add_argument('second', type=Path, help='Second saved raw stats snapshot')
    args = parser.parse_args()
    pair = stable_events(args.first.read_bytes(), args.second.read_bytes())
    print(json.dumps(dict(head=pair['head'], unstable_slots=pair['unstable_slots'],
                          summary=summarize_events(pair['events'])), indent=2))


if __name__ == '__main__':
    main()
