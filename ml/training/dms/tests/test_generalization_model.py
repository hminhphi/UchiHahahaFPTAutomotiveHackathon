import torch

from fleetiq_training_dms.model import VisualLandmarkGRU


def test_visual_landmark_gru_outputs_three_logits_per_window():
    model = VisualLandmarkGRU(pretrained=False)
    images = torch.zeros(2, 4, 3, 64, 64)
    landmarks = torch.zeros(2, 4, 18)
    assert model(images, landmarks).shape == (2, 3)
    assert not any(parameter.requires_grad for parameter in model.encoder.parameters())
