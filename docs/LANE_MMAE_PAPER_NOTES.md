# Lane MMAE paper notes for FleetIQ

Source: `paper/fmech-11-1436338.pdf`

Paper: Iman Fakhari and Sohel Anwar, "Computer vision model based robust lane detection using multiple model adaptive estimation methodology", Frontiers in Mechanical Engineering, 2025.

## Core idea

The paper does not propose one new lane detector. Its main contribution is a Multiple Model Adaptive Estimation (MMAE) framework that runs multiple lane-detection models and chooses the one whose lane offset best matches a reference estimator.

In the paper:

- Model 1 is a simpler CV pipeline with ROI, binarization, bird's-eye view and Hough transform.
- Model 2 uses calibration, ROI, Sobel/Saturation/Hue thresholding, sliding windows and polynomial fitting.
- A rear camera lane-offset model acts as a time-delayed reference.
- The front-camera offsets are compared against the delayed rear-camera offset.
- The final selected lane offset goes into a lane-keeping controller.

## Results worth citing

- Sharp turn case: Model 1 RMSE 21.12 cm, Model 2 RMSE 47.29 cm, final MMAE output RMSE 20.40 cm.
- Shadow case: final MMAE output improves RMSE versus both individual models by about 8-15%.
- The paper emphasizes that MMAE works when one model fails, but it may fail when all included models fail simultaneously.

## Mapping to this hackathon dataset

This dataset is not a clean lane-labeling benchmark. The visible road scene has many cases where lane markings are weak, partial, curved, occluded or visually ambiguous. The organizer labels also appear focused on front risk targets, not exhaustive scene annotation.

For FleetIQ, lane should therefore be used as a risk corridor, not as a full LKAS-grade controller signal.

Recommended adaptation:

- Use a Hough/edge lane model as Model 1.
- Use HSV/Sobel lane marking model as Model 2.
- Add a Model 3 lane-corridor prior from drivable road geometry.
- Fuse them with confidence and temporal consistency.
- Use the final lane mask/prism to filter object detections before distance/TTC.

## Practical interpretation

For collision risk, the important output is not perfect lane-line geometry. The useful output is:

- ego-lane floor mask,
- vertical risk prism above the lane,
- lane center estimate,
- lane offset estimate with confidence,
- object-in-corridor flag.

When lane markings are unreliable, the system should lower confidence and fall back to a conservative road corridor instead of forcing an incorrect offset.

## Local model audit update

The first local demo exposed two practical issues:

- A code bug made Model 1/2 fail after selecting Hough line pairs because two segment endpoints were passed into a fitting helper that expected at least 20 points. This is fixed in `scripts/roadface/demo_lane_mmae_offset.py`.
- Even after the bug fix, Model 1/2 should be treated as lane-marking diagnostics, not as the primary collision-risk mask. They are easily distracted by curbs, shadows, synthetic textures, road edges and curved scenes.

Current local interpretation:

- Model 1: Hough/edge can help on straight, well-marked roads, but should be rejected or down-weighted when it disagrees strongly with the metric ego corridor.
- Model 2: HSV/Sobel can recover color/edge lane markings, but is vulnerable to non-lane high-contrast regions.
- Model 3: metric ego-lane corridor from KITTI intrinsics plus depth support is the most stable mask for hackathon collision-risk filtering.

For the hackathon demo, the lane output should be described as an **ego-lane risk corridor**, not as a production lane-keeping lane detector. Use this corridor to filter vehicles/pedestrians/cyclists before distance, relative speed and TTC estimation.

Audit artifacts:

- `artifacts/roadface/lane_demo/lane_model_audit_T06.csv`
- `artifacts/roadface/lane_demo/lane_model_audit_T01.csv`
