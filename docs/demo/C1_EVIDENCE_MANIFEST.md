# Demo Evidence Manifest

| Surface | Evidence | Source label | Validation |
| --- | --- | --- | --- |
| Fleet priority | Six trips and transparent aggregate score | Organizer telemetry + documented FleetIQ baseline | `GET /api/v1/trips` |
| Road replay | `kitti/image_2` JPEG frame sequence | Historical organizer evidence | WebSocket ordered-frame smoke check |
| Current vehicle position | `ego.location.x/y` projected onto SVG route | Organizer simulator world position | Frame index shared with replay packet |
| Vehicle dynamics | Speed and long/lat acceleration | Organizer ego telemetry, physical clipping for display | `GET /trajectory`, 600 points |
| Driver state | State and alertness per frame | Organizer DMS reference label | Frame-aligned telemetry card |
| TTC and headway | Finite value only when source provides one | Organizer simulator reference | `No valid TTC` otherwise |
| Model endpoint | `/invocations` integration contract | Local deterministic mock | Compose smoke check |
| Coaching delivery | CarSky bridge acknowledge endpoint | Local mock bridge | Compose smoke check |

The manifest is intentionally conservative. It prevents a demo presenter from
calling reference labels a model result, or calling a mock endpoint live AWS
inference.
