"""Driver Sequence Neural Network Model Architecture (Bi-LSTM / Bi-GRU)."""

import torch
import torch.nn as nn
import timm


class DriverSequenceModel(nn.Module):
    """RNN (LSTM/GRU) Model for Driver State Time-Series Classification."""

    def __init__(
        self,
        feature_dim: int = 18,
        hidden_dim: int = 128,
        num_layers: int = 2,
        num_classes: int = 5,
        dropout: float = 0.2,
        cell_type: str = "lstm",
    ):
        super().__init__()
        self.cell_type = cell_type.lower()

        if self.cell_type == "lstm":
            self.rnn = nn.LSTM(
                input_size=feature_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
                bidirectional=True,
            )
        elif self.cell_type == "gru":
            self.rnn = nn.GRU(
                input_size=feature_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
                bidirectional=True,
            )
        else:
            raise ValueError(f"Unsupported cell_type '{cell_type}'. Choose 'lstm' or 'gru'.")

        rnn_out_dim = hidden_dim * 2

        self.classifier = nn.Sequential(
            nn.BatchNorm1d(rnn_out_dim),
            nn.Dropout(dropout),
            nn.Linear(rnn_out_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: [B, Seq_Len, Feature_Dim]
        rnn_out, _ = self.rnn(x)  # shape: [B, Seq_Len, Hidden_Dim * 2]
        last_step_out = rnn_out[:, -1, :]  # shape: [B, Hidden_Dim * 2]
        logits = self.classifier(last_step_out)
        return logits


def build_sequence_model(
    feature_dim: int = 18,
    hidden_dim: int = 128,
    num_layers: int = 2,
    num_classes: int = 5,
    cell_type: str = "lstm",
) -> DriverSequenceModel:
    """Helper factory function to construct a DriverSequenceModel."""
    return DriverSequenceModel(
        feature_dim=feature_dim,
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        num_classes=num_classes,
        cell_type=cell_type,
    )


class VisualLandmarkGRU(nn.Module):
    """Frozen image encoder plus landmark sequence classifier."""

    def __init__(
        self,
        image_model_name: str = "mobilenetv3_small_100",
        feature_dim: int = 18,
        hidden_dim: int = 128,
        num_classes: int = 3,
        pretrained: bool = True,
    ):
        super().__init__()
        self.encoder = timm.create_model(
            image_model_name,
            pretrained=pretrained,
            num_classes=0,
            global_pool="avg",
        )
        for parameter in self.encoder.parameters():
            parameter.requires_grad = False
        self.encoder.eval()
        with torch.no_grad():
            encoder_dim = self.encoder(torch.zeros(1, 3, 64, 64)).shape[-1]

        self.rnn = nn.GRU(
            input_size=encoder_dim + feature_dim,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=True,
        )
        self.classifier = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, images: torch.Tensor, landmarks: torch.Tensor) -> torch.Tensor:
        batch_size, sequence_length = images.shape[:2]
        with torch.no_grad():
            embeddings = self.encoder(images.flatten(0, 1)).reshape(batch_size, sequence_length, -1)
        fused = torch.cat((embeddings, landmarks), dim=-1)
        sequence, _ = self.rnn(fused)
        return self.classifier(sequence[:, -1, :])
