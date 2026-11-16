"""AURORA spatiotemporal patch dataset."""

import numpy as np
import torch
from torch.utils.data import Dataset


class SatellitePatchDataset(Dataset):

    def __init__(
        self,
        X,
        indices,
        patch_size=32,
        masks=None
    ):

        self.X = X[..., 0]
        self.patch = patch_size
        self.samples = []

        self.masks = (
            None if masks is None else masks[..., 0]
        )

        _, height, width = self.X.shape

        for pos, t in enumerate(indices):

            if t < 12:
                raise ValueError("Insufficient history")

            for y in range(0, height, patch_size):
                for x in range(0, width, patch_size):

                    target = self.X[
                        t,
                        y:y+patch_size,
                        x:x+patch_size
                    ]

                    valid = np.isfinite(target)

                    if self.masks is not None:
                        valid &= self.masks[
                            pos,
                            y:y+patch_size,
                            x:x+patch_size
                        ]

                    if valid.any():
                        self.samples.append(
                            (pos, int(t), y, x)
                        )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):

        pos, t, y, x = self.samples[index]
        p = self.patch

        history = self.X[
            t-12:t,
            y:y+p,
            x:x+p
        ]

        target = self.X[
            t,
            y:y+p,
            x:x+p
        ]

        h, w = target.shape

        observed = np.isfinite(history)
        valid = np.isfinite(target)

        if self.masks is not None:
            valid &= self.masks[
                pos, y:y+p, x:x+p
            ]

        inputs = np.zeros(
            (12, 2, p, p), dtype=np.float32
        )

        inputs[:, 0, :h, :w] = np.nan_to_num(
            history, nan=0.0
        )

        inputs[:, 1, :h, :w] = observed

        labels = np.zeros(
            (1, p, p), dtype=np.float32
        )

        labels[0, :h, :w] = np.nan_to_num(
            target, nan=0.0
        )

        mask = np.zeros(
            (1, p, p), dtype=bool
        )

        mask[0, :h, :w] = valid

        return (
            torch.from_numpy(inputs),
            torch.from_numpy(labels),
            torch.from_numpy(mask)
        )
