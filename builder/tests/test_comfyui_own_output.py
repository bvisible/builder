# //// Neoffice — added file (no upstream equivalent): two image calls in flight on one ComfyUI never get each
# //// other's picture (builder/site_ai/generators/comfyui_client.py, neoffice-maintenance#2052).
import json
import threading
import unittest
from unittest.mock import patch

from builder.site_ai.generators import comfyui_client


class FakeComfyUI:
	"""Two workers that share one output folder and number their files themselves: both calls of two builds
	running at once save `<prefix>_00001_.png`, and the second write wins."""

	def __init__(self):
		self.lock = threading.Lock()
		self.queued = {}  # prompt id -> (prefix, prompt text)
		self.files = {}  # file name -> bytes
		self.prefixes = []
		self.both_in_flight = threading.Event()

	def post(self, url, headers=None, data=None, timeout=None):
		workflow = json.loads(data)["prompt"]
		saver = next(n for n in workflow.values() if n["class_type"] == "SaveImage")
		text = next(
			(n["inputs"]["text"] for n in workflow.values() if n["class_type"] == "CLIPTextEncode"), ""
		)
		with self.lock:
			pid = f"p{len(self.queued) + 1}"
			self.queued[pid] = (saver["inputs"]["filename_prefix"], text)
			self.prefixes.append(saver["inputs"]["filename_prefix"])
			if len(self.queued) == 2:  # both in flight: both workers render and save
				for prefix, prompt in self.queued.values():
					self.files[f"{prefix}_00001_.png"] = f"picture of {prompt}".encode()
				self.both_in_flight.set()
		return Response({"prompt_id": pid})

	def get(self, url, headers=None, timeout=None):
		if "/history/" in url:
			pid = url.rsplit("/", 1)[1]
			if not self.both_in_flight.wait(5):
				return Response({})
			prefix = self.queued[pid][0]
			image = {"filename": f"{prefix}_00001_.png", "subfolder": "", "type": "output"}
			return Response(
				{pid: {"status": {"status_str": "success"}, "outputs": {"10": {"images": [image]}}}}
			)
		name = url.split("filename=", 1)[1].split("&", 1)[0]
		return Response(content=self.files.get(name, b""))


class Response:
	def __init__(self, payload=None, content=b""):
		self.payload, self.content, self.ok = payload, content, True

	def json(self):
		return self.payload


class TestComfyUIOwnOutput(unittest.TestCase):
	def generate_two_at_once(self):
		fake = FakeComfyUI()
		saved = {}

		def build(prompt):
			try:
				saved[prompt] = comfyui_client.generate_image(prompt, 512, 512)
			except Exception as e:
				saved[prompt] = f"failed: {e}"

		with (
			patch.object(comfyui_client, "_settings", return_value=("https://comfy.test", "key")),
			patch.object(comfyui_client.requests, "post", side_effect=fake.post),
			patch.object(comfyui_client.requests, "get", side_effect=fake.get),
			patch.object(comfyui_client, "_save_png", side_effect=lambda content, prefix: content.decode()),
			patch.object(comfyui_client.time, "sleep"),
			patch.object(comfyui_client, "ai_log"),
		):
			threads = [
				threading.Thread(target=build, args=(p,)) for p in ("a loaf of bread", "roasted coffee")
			]
			for thread in threads:
				thread.start()
			for thread in threads:
				thread.join(10)
		return fake, saved

	def test_two_builds_at_once_each_get_their_own_picture(self):
		fake, saved = self.generate_two_at_once()
		self.assertEqual(
			saved,
			{"a loaf of bread": "picture of a loaf of bread", "roasted coffee": "picture of roasted coffee"},
		)
		self.assertEqual(len(set(fake.prefixes)), 2)

	def test_a_picture_of_another_call_is_refused(self):
		history = {
			"p1": {
				"status": {"status_str": "success"},
				"outputs": {
					"10": {"images": [{"filename": "gen_00007_.png", "subfolder": "", "type": "output"}]}
				},
			}
		}
		with (
			patch.object(comfyui_client, "_settings", return_value=("https://comfy.test", "key")),
			patch.object(comfyui_client.requests, "post", return_value=Response({"prompt_id": "p1"})),
			patch.object(
				comfyui_client.requests,
				"get",
				side_effect=lambda url, **kw: Response(history)
				if "/history/" in url
				else Response(content=b"x"),
			),
		):
			with self.assertRaises(RuntimeError):
				comfyui_client._run_workflow(json.loads(json.dumps(comfyui_client._WF_GENERATE)))


class TestComfyUIPromptIdOutput(unittest.TestCase):
	"""The fleet's ComfyUI server ignores `filename_prefix` and names every output `<prompt_id>.png` (osiris,
	11.11.2026, neoffice-maintenance#2573): the own-prefix check alone refused every picture, so no site photo and no
	logo came back. A file named by this call's prompt id is this call's; another call's is still refused."""

	def run_with_outputs(self, filenames):
		history = {
			"p1": {
				"status": {"status_str": "success"},
				"outputs": {
					"10": {
						"images": [
							{"filename": name, "subfolder": "", "type": "output"} for name in filenames
						]
					}
				},
			}
		}
		served = []

		def get(url, **kw):
			if "/history/" in url:
				return Response(history)
			name = url.split("filename=", 1)[1].split("&", 1)[0]
			served.append(name)
			return Response(content=f"bytes of {name}".encode())

		with (
			patch.object(comfyui_client, "_settings", return_value=("https://comfy.test", "key")),
			patch.object(comfyui_client.requests, "post", return_value=Response({"prompt_id": "p1"})),
			patch.object(comfyui_client.requests, "get", side_effect=get),
		):
			result = comfyui_client._run_workflow(json.loads(json.dumps(comfyui_client._WF_GENERATE)))
		return result, served

	def test_a_picture_named_by_its_own_prompt_id_is_taken(self):
		result, served = self.run_with_outputs(["p1.png"])
		self.assertEqual(result, b"bytes of p1.png")
		self.assertEqual(served, ["p1.png"])

	def test_a_picture_named_by_another_prompt_id_is_still_refused(self):
		with self.assertRaises(RuntimeError):
			self.run_with_outputs(["p2.png"])
