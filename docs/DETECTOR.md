# Training the detector

The local object detector (`pipeline/src/routine_watch/detector.py`, SPEC §6.1 and
§16) finds task objects in one frame and reports them as boxes. It always runs
**locally**, from weights downloaded after training - Roboflow's hosted inference is
never called from code, tests or CI (AGENTS.md), and Roboflow credits are scarce (50/
month): humans run the training, at most 2-3 times.

This file is two things: the labelling list for Ian's Roboflow project, and how to
turn a trained model into `models/detector.onnx` on his own GPU.

## Classes to label

One Roboflow project, all the classes every task needs so one training run covers
them all. `routine_watch.contracts.ObjectLabel` is the source of truth; this list has
to match it, alias rows included so a labeller knows which word to use.

| Class (exact name in Roboflow) | Task | Notes |
|---|---|---|
| `kettle` | tea | on its base, carried, held over the cup |
| `cup` | tea | |
| `teabag` | tea | on the counter, in the cup, lifted out |
| `spoon` | tea | also stirs the sugar in |
| `milk` | tea | carton or jug, held over the cup |
| `sugar` | tea | bowl, jar or packet, held over the cup |
| `pill_bottle` | meds | |
| `pill_organiser` | meds | the weekly dosette box, shut and open |
| `glass` | meds | |
| `water_jug` | meds, protein shake | doubles as the shake's water bottle - label a water bottle under this class too, not a new one |
| `shaker` | protein shake | shaker bottle / blender bottle, lid on and off |
| `protein_tub` | protein shake | the tub the powder comes in, lid on and off |
| `scoop` | protein shake | the scoop that goes in and out of the tub |
| `hand` | all | optional: only label this if you are not exporting MediaPipe hand boxes instead (`capture.py` prefers MediaPipe's own landmarks when they are present) |
| `pouring` | tea | optional: the act of pouring itself, not an object - label a tight box around the stream/tilt when it's visible |

Label every class across a range of lighting, distances and the usual kitchen
clutter; `routine_watch.detector.label_for` matches names case- and
punctuation-insensitively and `LABEL_ALIASES` covers a few obvious synonyms (`mug` for
`cup`, `blender_bottle` for `shaker`, ...), but the class list above is what the model
should actually be trained on. A class the running weights were never trained on is
simply never reported - nothing downstream breaks, that task's steps just never
recognise - so the two class lists (here and `ObjectLabel`) are allowed to land one
training run apart.

## Training on your own GPU

Roboflow trains in the browser too, but humans only get 2-3 runs a month out of it
and this project needs more iteration than that, so train locally and only use
Roboflow to hold and export the labelled dataset.

1. **Export the labelled dataset** from the Roboflow project in YOLOv8/YOLO11 format
   (Roboflow → your project → Versions → Export Dataset → "YOLOv8"). Unzip it
   somewhere on the training machine; it comes with a `data.yaml` listing the classes.

2. **Install PyTorch for your CUDA version.** On a machine with CUDA 12.8 drivers:

   ```sh
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
   pip install ultralytics
   ```

   Check the install picked up the GPU before spending an hour on a CPU run:

   ```sh
   python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```

3. **Train a YOLO11n model** (the nano size: this only has to tell a dozen kitchen
   objects apart, not run a general-purpose detector, and a small model is what keeps
   inference fast on a laptop with no GPU at the demo):

   ```sh
   yolo task=detect mode=train model=yolo11n.pt data=/path/to/data.yaml \
       epochs=100 imgsz=640 device=0
   ```

   `yolo11n.pt` downloads automatically the first time. Training writes
   `runs/detect/train/weights/best.pt`; watch `mAP50` in the printed table and stop
   early (`epochs=` lower, or ctrl-C - the latest checkpoint is kept) once it plateaus.

4. **Export to ONNX**, which is what `routine_watch.detector.LocalDetector` runs
   through `onnxruntime` with no extra install on the demo machine:

   ```sh
   yolo export model=runs/detect/train/weights/best.pt format=onnx imgsz=640
   ```

   This writes `best.onnx` next to the `.pt` file, with the class names embedded in
   its metadata (`detector.py`'s `_onnx_names` reads them straight out of it, so
   nothing else needs to list them again). Copy it into the repo:

   ```sh
   cp runs/detect/train/weights/best.onnx models/detector.onnx
   ```

5. **Run it**:

   ```sh
   export DETECTOR_WEIGHTS=models/detector.onnx
   scripts/camera.sh
   ```

   Without this env var, capture falls back to `FakeDetector` and reports no objects
   at all - the normal state for everyone who is not Ian's training machine, and
   exactly what tests, CI and the scenario replay use (AGENTS.md: never real inference
   in code, tests or CI).

Weights are never committed to git (binary, and large); `models/` is gitignored.
Re-running step 3 after adding protein-shake examples to the dataset, then steps 4-5,
is the whole loop for improving the model - no code changes needed, because
`tasks/protein_shake.yaml` and the three classes above are the entire feature
(`test_protein_shake.py`'s point, same as `test_meds_graph.py`'s for the task before
it).
