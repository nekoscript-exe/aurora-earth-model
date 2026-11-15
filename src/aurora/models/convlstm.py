"""AURORA spatiotemporal neural network."""

import torch
from torch import nn


class ConvLSTMCell(nn.Module):

    def __init__(self, input_channels, hidden_channels):
        super().__init__()

        self.hidden_channels = hidden_channels

        self.gates = nn.Conv2d(
            input_channels + hidden_channels,
            4 * hidden_channels,
            kernel_size=3,
            padding=1
        )

    def forward(self, x, state=None):

        if state is None:
            shape = (
                x.shape[0],
                self.hidden_channels,
                x.shape[2],
                x.shape[3]
            )

            h = x.new_zeros(shape)
            c = x.new_zeros(shape)

        else:
            h, c = state

        combined = torch.cat([x, h], dim=1)

        i, f, o, g = self.gates(
            combined
        ).chunk(4, dim=1)

        i = torch.sigmoid(i)
        f = torch.sigmoid(f)
        o = torch.sigmoid(o)
        g = torch.tanh(g)

        c = f * c + i * g
        h = o * torch.tanh(c)

        return h, c


class AuroraConvLSTM(nn.Module):

    def __init__(self, output_activation="tanh"):
        super().__init__()
        if output_activation not in ("tanh", "linear"):
            raise ValueError("Unknown output activation")
        self.output_activation = output_activation

        self.layer1 = ConvLSTMCell(2, 16)
        self.layer2 = ConvLSTMCell(16, 32)

        self.head = nn.Conv2d(
            32, 1, kernel_size=1
        )

    def forward(self, x):
        state1 = None
        state2 = None

        for t in range(x.shape[1]):

            state1 = self.layer1(
                x[:, t], state1
            )

            state2 = self.layer2(
                state1[0], state2
            )

        if state2 is None:
            raise ValueError("ConvLSTM requires at least one input time step")
        output = self.head(state2[0])
        return torch.tanh(output) if self.output_activation == "tanh" else output
