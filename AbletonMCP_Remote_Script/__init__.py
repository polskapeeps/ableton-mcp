# AbletonMCP Remote Script
from __future__ import absolute_import, print_function, unicode_literals

import json
import socket
import threading
import time
import traceback

from _Framework.ControlSurface import ControlSurface

try:
    import Queue as queue
except ImportError:
    import queue


DEFAULT_PORT = 9877
HOST = "127.0.0.1"


def create_instance(c_instance):
    return AbletonMCP(c_instance)


class AbletonMCPError(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code
        self.message = message


class AbletonMCP(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self.log_message("AbletonMCP Remote Script initializing")

        self.server = None
        self.server_thread = None
        self.client_threads = []
        self.running = False
        self._song = self.song()

        self._command_handlers = {
            "live_status": self._cmd_live_status,
            "list_tracks": self._cmd_list_tracks,
            "list_scenes": self._cmd_list_scenes,
            "list_clip_slots": self._cmd_list_clip_slots,
            "list_devices": self._cmd_list_devices,
            "list_parameters": self._cmd_list_parameters,
            "inspect_device_chain": self._cmd_inspect_device_chain,
            "list_nested_device_parameters": self._cmd_list_nested_device_parameters,
            "transport_play": self._cmd_transport_play,
            "transport_continue": self._cmd_transport_continue,
            "transport_stop": self._cmd_transport_stop,
            "transport_set_tempo": self._cmd_transport_set_tempo,
            "transport_set_metronome": self._cmd_transport_set_metronome,
            "track_create_midi": self._cmd_track_create_midi,
            "track_create_audio": self._cmd_track_create_audio,
            "track_rename": self._cmd_track_rename,
            "track_set_color": self._cmd_track_set_color,
            "track_set_arm": self._cmd_track_set_arm,
            "track_set_mute": self._cmd_track_set_mute,
            "track_set_solo": self._cmd_track_set_solo,
            "track_set_volume": self._cmd_track_set_volume,
            "track_set_pan": self._cmd_track_set_pan,
            "track_set_send": self._cmd_track_set_send,
            "track_stop_all_clips": self._cmd_track_stop_all_clips,
            "track_duplicate": self._cmd_track_duplicate,
            "track_delete": self._cmd_track_delete,
            "scene_create": self._cmd_scene_create,
            "scene_launch": self._cmd_scene_launch,
            "scene_rename": self._cmd_scene_rename,
            "scene_set_color": self._cmd_scene_set_color,
            "scene_duplicate": self._cmd_scene_duplicate,
            "scene_delete": self._cmd_scene_delete,
            "clip_create_midi": self._cmd_clip_create_midi,
            "clip_fire": self._cmd_clip_fire,
            "clip_stop": self._cmd_clip_stop,
            "clip_rename": self._cmd_clip_rename,
            "clip_set_color": self._cmd_clip_set_color,
            "clip_set_loop": self._cmd_clip_set_loop,
            "clip_add_notes": self._cmd_clip_add_notes,
            "clip_duplicate": self._cmd_clip_duplicate,
            "clip_delete": self._cmd_clip_delete,
            "device_set_parameter": self._cmd_device_set_parameter,
            "nested_device_set_parameter": self._cmd_nested_device_set_parameter,
            "device_delete": self._cmd_device_delete,
        }

        self.start_server()
        self.show_message("AbletonMCP: Listening on port {0}".format(DEFAULT_PORT))

    def disconnect(self):
        self.log_message("AbletonMCP disconnecting")
        self.running = False

        if self.server:
            try:
                self.server.close()
            except Exception:
                pass

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(1.0)

        ControlSurface.disconnect(self)
        self.log_message("AbletonMCP disconnected")

    def start_server(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, DEFAULT_PORT))
            self.server.listen(5)
            self.server.settimeout(1.0)

            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            self.log_message("AbletonMCP bridge listening on {0}:{1}".format(HOST, DEFAULT_PORT))
        except Exception as exc:
            self.log_message("Error starting socket server: {0}".format(exc))
            self.show_message("AbletonMCP: failed to start bridge")

    def _server_loop(self):
        while self.running:
            try:
                client, address = self.server.accept()
            except socket.timeout:
                continue
            except Exception as exc:
                if self.running:
                    self.log_message("Socket accept error: {0}".format(exc))
                time.sleep(0.25)
                continue

            self.log_message("Client connected from {0}".format(address))
            thread = threading.Thread(target=self._handle_client, args=(client,))
            thread.daemon = True
            thread.start()
            self.client_threads.append(thread)
            self.client_threads = [item for item in self.client_threads if item.is_alive()]

    def _handle_client(self, client):
        buffer = ""
        client.settimeout(None)

        try:
            while self.running:
                chunk = client.recv(65536)
                if not chunk:
                    break

                try:
                    buffer += chunk.decode("utf-8")
                except AttributeError:
                    buffer += chunk

                while "\n" in buffer:
                    raw_message, buffer = buffer.split("\n", 1)
                    if not raw_message.strip():
                        continue

                    try:
                        command = json.loads(raw_message)
                        response = self._process_command(command)
                    except ValueError as exc:
                        response = self._error("invalid_request", "Invalid JSON: {0}".format(exc))
                    except Exception as exc:
                        response = self._error("remote_error", str(exc))

                    payload = json.dumps(response)
                    try:
                        client.sendall(payload.encode("utf-8") + b"\n")
                    except AttributeError:
                        client.sendall(payload + "\n")
        except Exception as exc:
            self.log_message("Client handler error: {0}".format(exc))
            self.log_message(traceback.format_exc())
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _process_command(self, command):
        command_type = command.get("type")
        params = command.get("params") or {}
        handler = self._command_handlers.get(command_type)

        if handler is None:
            return self._error("invalid_request", "Unknown command: {0}".format(command_type))

        return self._run_on_main_thread(handler, params)

    def _run_on_main_thread(self, handler, params):
        response_queue = queue.Queue()

        def task():
            try:
                response_queue.put(handler(params))
            except AbletonMCPError as exc:
                response_queue.put(self._error(exc.code, exc.message))
            except Exception as exc:
                self.log_message("Main thread task failed: {0}".format(exc))
                self.log_message(traceback.format_exc())
                response_queue.put(self._error("remote_error", str(exc)))

        try:
            self.schedule_message(0, task)
        except AssertionError:
            task()

        try:
            return response_queue.get(timeout=15.0)
        except queue.Empty:
            return self._error("remote_error", "Timed out waiting for Ableton to process command")

    def _ok(self, object_type, object_ref, state):
        return {
            "ok": True,
            "error": None,
            "object_type": object_type,
            "object_ref": object_ref or {},
            "state": state,
        }

    def _error(self, code, message, object_type=None, object_ref=None, state=None):
        return {
            "ok": False,
            "error": {"code": code, "message": message},
            "object_type": object_type,
            "object_ref": object_ref or {},
            "state": state,
        }

    def _cmd_live_status(self, params):
        return self._ok("song", {}, self._song_state())

    def _cmd_list_tracks(self, params):
        tracks = []
        for index, track in enumerate(self._song.tracks):
            tracks.append(self._track_state(track, index))
        return self._ok("track_collection", {}, {"tracks": tracks, "count": len(tracks)})

    def _cmd_list_scenes(self, params):
        scenes = []
        for index, scene in enumerate(self._song.scenes):
            scenes.append(self._scene_state(scene, index))
        return self._ok("scene_collection", {}, {"scenes": scenes, "count": len(scenes)})

    def _cmd_list_clip_slots(self, params):
        track_index = self._require_int(params, "track_index")
        track = self._require_track(track_index)
        clip_slots = []
        for slot_index, clip_slot in enumerate(track.clip_slots):
            clip_slots.append(self._clip_slot_state(track, track_index, clip_slot, slot_index))
        return self._ok(
            "clip_slot_collection",
            {"track_index": track_index},
            {"track": self._track_state(track, track_index), "clip_slots": clip_slots},
        )

    def _cmd_list_devices(self, params):
        track_index = self._require_int(params, "track_index")
        track = self._require_track(track_index)
        devices = []
        for device_index, device in enumerate(track.devices):
            devices.append(self._device_state(device, track_index, device_index))
        return self._ok(
            "device_collection",
            {"track_index": track_index},
            {"track": self._track_state(track, track_index), "devices": devices},
        )

    def _cmd_list_parameters(self, params):
        track_index = self._require_int(params, "track_index")
        device_index = self._require_int(params, "device_index")
        track = self._require_track(track_index)
        device = self._require_device(track, track_index, device_index)
        parameters = []
        for parameter_index, parameter in enumerate(device.parameters):
            parameters.append(self._parameter_state(parameter, track_index, device_index, parameter_index))
        return self._ok(
            "parameter_collection",
            {"track_index": track_index, "device_index": device_index},
            {"device": self._device_state(device, track_index, device_index), "parameters": parameters},
        )

    def _cmd_inspect_device_chain(self, params):
        track_index = self._require_int(params, "track_index")
        include_parameters = bool(params.get("include_parameters", True))
        max_depth = int(params.get("max_depth", 6))
        track = self._require_track(track_index)

        devices = []
        for device_index, device in enumerate(track.devices):
            devices.append(
                self._device_tree(
                    track_index,
                    device,
                    [device_index],
                    [],
                    [],
                    include_parameters,
                    max_depth,
                    0,
                )
            )

        state = {
            "track": self._track_state(track, track_index),
            "devices": devices,
            "include_parameters": include_parameters,
            "max_depth": max_depth,
        }
        return self._ok("device_tree", {"track_index": track_index}, state)

    def _cmd_list_nested_device_parameters(self, params):
        track_index = self._require_int(params, "track_index")
        device_path = self._normalize_index_list(self._require_value(params, "device_path"), "device_path")
        chain_path = self._normalize_index_list(params.get("chain_path", []), "chain_path")
        chain_type_path = self._normalize_chain_types(params.get("chain_type_path", []))
        track = self._require_track(track_index)

        device = self._resolve_nested_device(track, device_path, chain_path, chain_type_path)
        parameter_states = []
        for parameter_index, parameter in enumerate(device.parameters):
            parameter_states.append(
                self._parameter_state(
                    parameter,
                    track_index,
                    device_path[-1],
                    parameter_index,
                    device_path=device_path,
                    chain_path=chain_path,
                    chain_type_path=chain_type_path,
                )
            )

        state = {
            "device": self._device_state(
                device,
                track_index,
                device_path[-1],
                device_path=device_path,
                chain_path=chain_path,
                chain_type_path=chain_type_path,
                include_parameters=False,
            ),
            "parameters": parameter_states,
        }
        return self._ok(
            "parameter_collection",
            {
                "track_index": track_index,
                "device_path": device_path,
                "chain_path": chain_path,
                "chain_type_path": chain_type_path,
            },
            state,
        )

    def _cmd_transport_play(self, params):
        self._song.start_playing()
        return self._ok("song", {}, self._song_state())

    def _cmd_transport_continue(self, params):
        self._song.continue_playing()
        return self._ok("song", {}, self._song_state())

    def _cmd_transport_stop(self, params):
        self._song.stop_playing()
        return self._ok("song", {}, self._song_state())

    def _cmd_transport_set_tempo(self, params):
        tempo = float(self._require_value(params, "tempo"))
        self._song.tempo = tempo
        return self._ok("song", {}, self._song_state())

    def _cmd_transport_set_metronome(self, params):
        enabled = bool(self._require_value(params, "enabled"))
        self._song.metronome = enabled
        return self._ok("song", {}, self._song_state())

    def _cmd_track_create_midi(self, params):
        index = int(params.get("index", -1))
        self._song.create_midi_track(index)
        new_index = len(self._song.tracks) - 1 if index == -1 else index
        track = self._require_track(new_index)
        return self._ok("track", {"track_index": new_index}, self._track_state(track, new_index))

    def _cmd_track_create_audio(self, params):
        index = int(params.get("index", -1))
        self._song.create_audio_track(index)
        new_index = len(self._song.tracks) - 1 if index == -1 else index
        track = self._require_track(new_index)
        return self._ok("track", {"track_index": new_index}, self._track_state(track, new_index))

    def _cmd_track_rename(self, params):
        track_index = self._require_int(params, "track_index")
        name = self._require_text(params, "name")
        track = self._require_track(track_index)
        track.name = name
        return self._ok("track", {"track_index": track_index}, self._track_state(track, track_index))

    def _cmd_track_set_color(self, params):
        track_index = self._require_int(params, "track_index")
        color = int(self._require_value(params, "color"))
        track = self._require_track(track_index)
        self._set_attr(track, "color", color, "track color")
        return self._ok("track", {"track_index": track_index}, self._track_state(track, track_index))

    def _cmd_track_set_arm(self, params):
        track_index = self._require_int(params, "track_index")
        armed = bool(self._require_value(params, "armed"))
        track = self._require_track(track_index)
        if not getattr(track, "can_be_armed", False):
            raise AbletonMCPError("unsupported_operation", "Track cannot be armed")
        track.arm = armed
        return self._ok("track", {"track_index": track_index}, self._track_state(track, track_index))

    def _cmd_track_set_mute(self, params):
        track_index = self._require_int(params, "track_index")
        muted = bool(self._require_value(params, "muted"))
        track = self._require_track(track_index)
        track.mute = muted
        return self._ok("track", {"track_index": track_index}, self._track_state(track, track_index))

    def _cmd_track_set_solo(self, params):
        track_index = self._require_int(params, "track_index")
        soloed = bool(self._require_value(params, "soloed"))
        track = self._require_track(track_index)
        track.solo = soloed
        return self._ok("track", {"track_index": track_index}, self._track_state(track, track_index))

    def _cmd_track_set_volume(self, params):
        track_index = self._require_int(params, "track_index")
        value = float(self._require_value(params, "value"))
        track = self._require_track(track_index)
        self._set_parameter(track.mixer_device.volume, value=value)
        return self._ok("track", {"track_index": track_index}, self._track_state(track, track_index))

    def _cmd_track_set_pan(self, params):
        track_index = self._require_int(params, "track_index")
        value = float(self._require_value(params, "value"))
        track = self._require_track(track_index)
        self._set_parameter(track.mixer_device.panning, value=value)
        return self._ok("track", {"track_index": track_index}, self._track_state(track, track_index))

    def _cmd_track_set_send(self, params):
        track_index = self._require_int(params, "track_index")
        send_index = self._require_int(params, "send_index")
        value = float(self._require_value(params, "value"))
        track = self._require_track(track_index)

        if send_index < 0 or send_index >= len(track.mixer_device.sends):
            raise AbletonMCPError("invalid_index", "Send index out of range")

        self._set_parameter(track.mixer_device.sends[send_index], value=value)
        return self._ok("track", {"track_index": track_index}, self._track_state(track, track_index))

    def _cmd_track_stop_all_clips(self, params):
        track_index = self._require_int(params, "track_index")
        track = self._require_track(track_index)
        track.stop_all_clips()
        return self._ok("track", {"track_index": track_index}, self._track_state(track, track_index))

    def _cmd_track_duplicate(self, params):
        self._require_confirmed(params)
        track_index = self._require_int(params, "track_index")
        self._require_track(track_index)
        self._song.duplicate_track(track_index)
        new_index = min(track_index + 1, len(self._song.tracks) - 1)
        track = self._require_track(new_index)
        return self._ok("track", {"track_index": new_index}, self._track_state(track, new_index))

    def _cmd_track_delete(self, params):
        self._require_confirmed(params)
        track_index = self._require_int(params, "track_index")
        self._require_track(track_index)
        self._song.delete_track(track_index)
        state = {"deleted_track_index": track_index, "remaining_track_count": len(self._song.tracks)}
        return self._ok("track", {"track_index": track_index}, state)

    def _cmd_scene_create(self, params):
        index = int(params.get("index", -1))
        self._song.create_scene(index)
        new_index = len(self._song.scenes) - 1 if index == -1 else index
        scene = self._require_scene(new_index)
        return self._ok("scene", {"scene_index": new_index}, self._scene_state(scene, new_index))

    def _cmd_scene_launch(self, params):
        scene_index = self._require_int(params, "scene_index")
        scene = self._require_scene(scene_index)
        scene.fire()
        return self._ok("scene", {"scene_index": scene_index}, self._scene_state(scene, scene_index))

    def _cmd_scene_rename(self, params):
        scene_index = self._require_int(params, "scene_index")
        name = self._require_text(params, "name")
        scene = self._require_scene(scene_index)
        scene.name = name
        return self._ok("scene", {"scene_index": scene_index}, self._scene_state(scene, scene_index))

    def _cmd_scene_set_color(self, params):
        scene_index = self._require_int(params, "scene_index")
        color = int(self._require_value(params, "color"))
        scene = self._require_scene(scene_index)
        self._set_attr(scene, "color", color, "scene color")
        return self._ok("scene", {"scene_index": scene_index}, self._scene_state(scene, scene_index))

    def _cmd_scene_duplicate(self, params):
        self._require_confirmed(params)
        scene_index = self._require_int(params, "scene_index")
        self._require_scene(scene_index)
        self._song.duplicate_scene(scene_index)
        new_index = min(scene_index + 1, len(self._song.scenes) - 1)
        scene = self._require_scene(new_index)
        return self._ok("scene", {"scene_index": new_index}, self._scene_state(scene, new_index))

    def _cmd_scene_delete(self, params):
        self._require_confirmed(params)
        scene_index = self._require_int(params, "scene_index")
        self._require_scene(scene_index)
        self._song.delete_scene(scene_index)
        state = {"deleted_scene_index": scene_index, "remaining_scene_count": len(self._song.scenes)}
        return self._ok("scene", {"scene_index": scene_index}, state)

    def _cmd_clip_create_midi(self, params):
        track_index = self._require_int(params, "track_index")
        clip_slot_index = self._require_int(params, "clip_slot_index")
        length = float(params.get("length", 4.0))
        track = self._require_track(track_index)

        if not getattr(track, "has_midi_input", False):
            raise AbletonMCPError("unsupported_operation", "Clip creation in session view requires a MIDI track")

        clip_slot = self._require_clip_slot(track, track_index, clip_slot_index)
        if clip_slot.has_clip:
            raise AbletonMCPError("invalid_request", "Clip slot already contains a clip")

        clip_slot.create_clip(length)
        clip = self._require_clip(track, track_index, clip_slot_index)
        return self._ok(
            "clip",
            {"track_index": track_index, "clip_slot_index": clip_slot_index},
            self._clip_state(clip, track_index, clip_slot_index),
        )

    def _cmd_clip_fire(self, params):
        track_index = self._require_int(params, "track_index")
        clip_slot_index = self._require_int(params, "clip_slot_index")
        track = self._require_track(track_index)
        clip_slot = self._require_clip_slot(track, track_index, clip_slot_index)
        clip_slot.fire()
        return self._ok(
            "clip_slot",
            {"track_index": track_index, "clip_slot_index": clip_slot_index},
            self._clip_slot_state(track, track_index, clip_slot, clip_slot_index),
        )

    def _cmd_clip_stop(self, params):
        track_index = self._require_int(params, "track_index")
        clip_slot_index = self._require_int(params, "clip_slot_index")
        track = self._require_track(track_index)
        clip_slot = self._require_clip_slot(track, track_index, clip_slot_index)
        clip_slot.stop()
        return self._ok(
            "clip_slot",
            {"track_index": track_index, "clip_slot_index": clip_slot_index},
            self._clip_slot_state(track, track_index, clip_slot, clip_slot_index),
        )

    def _cmd_clip_rename(self, params):
        track_index = self._require_int(params, "track_index")
        clip_slot_index = self._require_int(params, "clip_slot_index")
        name = self._require_text(params, "name")
        track = self._require_track(track_index)
        clip = self._require_clip(track, track_index, clip_slot_index)
        clip.name = name
        return self._ok(
            "clip",
            {"track_index": track_index, "clip_slot_index": clip_slot_index},
            self._clip_state(clip, track_index, clip_slot_index),
        )

    def _cmd_clip_set_color(self, params):
        track_index = self._require_int(params, "track_index")
        clip_slot_index = self._require_int(params, "clip_slot_index")
        color = int(self._require_value(params, "color"))
        track = self._require_track(track_index)
        clip = self._require_clip(track, track_index, clip_slot_index)
        self._set_attr(clip, "color", color, "clip color")
        return self._ok(
            "clip",
            {"track_index": track_index, "clip_slot_index": clip_slot_index},
            self._clip_state(clip, track_index, clip_slot_index),
        )

    def _cmd_clip_set_loop(self, params):
        track_index = self._require_int(params, "track_index")
        clip_slot_index = self._require_int(params, "clip_slot_index")
        loop_start = float(self._require_value(params, "loop_start"))
        loop_end = float(self._require_value(params, "loop_end"))
        looping = bool(params.get("looping", True))

        if loop_end <= loop_start:
            raise AbletonMCPError("invalid_request", "loop_end must be greater than loop_start")

        track = self._require_track(track_index)
        clip = self._require_clip(track, track_index, clip_slot_index)
        self._set_attr(clip, "looping", looping, "clip looping")
        clip.loop_start = loop_start
        clip.loop_end = loop_end
        return self._ok(
            "clip",
            {"track_index": track_index, "clip_slot_index": clip_slot_index},
            self._clip_state(clip, track_index, clip_slot_index),
        )

    def _cmd_clip_add_notes(self, params):
        track_index = self._require_int(params, "track_index")
        clip_slot_index = self._require_int(params, "clip_slot_index")
        notes = params.get("notes") or []

        if not isinstance(notes, list):
            raise AbletonMCPError("invalid_request", "notes must be a list")

        track = self._require_track(track_index)
        clip = self._require_clip(track, track_index, clip_slot_index)

        if not getattr(clip, "is_midi_clip", False):
            raise AbletonMCPError("unsupported_operation", "Only MIDI clips can receive notes")

        live_notes = []
        for note in notes:
            if not isinstance(note, dict):
                raise AbletonMCPError("invalid_request", "Each note must be an object")

            live_notes.append(
                (
                    int(note.get("pitch", 60)),
                    float(note.get("start_time", 0.0)),
                    float(note.get("duration", 0.25)),
                    int(note.get("velocity", 100)),
                    bool(note.get("mute", False)),
                )
            )

        clip.set_notes(tuple(live_notes))
        state = self._clip_state(clip, track_index, clip_slot_index)
        state["added_note_count"] = len(live_notes)
        return self._ok("clip", {"track_index": track_index, "clip_slot_index": clip_slot_index}, state)

    def _cmd_clip_duplicate(self, params):
        self._require_confirmed(params)
        track_index = self._require_int(params, "track_index")
        clip_slot_index = self._require_int(params, "clip_slot_index")
        track = self._require_track(track_index)
        self._require_clip(track, track_index, clip_slot_index)
        track.duplicate_clip_slot(clip_slot_index)

        new_slot_index = min(clip_slot_index + 1, len(track.clip_slots) - 1)
        clip = self._require_clip(track, track_index, new_slot_index)
        return self._ok(
            "clip",
            {"track_index": track_index, "clip_slot_index": new_slot_index},
            self._clip_state(clip, track_index, new_slot_index),
        )

    def _cmd_clip_delete(self, params):
        self._require_confirmed(params)
        track_index = self._require_int(params, "track_index")
        clip_slot_index = self._require_int(params, "clip_slot_index")
        track = self._require_track(track_index)
        clip_slot = self._require_clip_slot(track, track_index, clip_slot_index)

        if not clip_slot.has_clip:
            raise AbletonMCPError("object_missing", "Clip slot does not contain a clip")

        clip_slot.delete_clip()
        return self._ok(
            "clip_slot",
            {"track_index": track_index, "clip_slot_index": clip_slot_index},
            self._clip_slot_state(track, track_index, clip_slot, clip_slot_index),
        )

    def _cmd_device_set_parameter(self, params):
        track_index = self._require_int(params, "track_index")
        device_index = self._require_int(params, "device_index")
        parameter_index = self._require_int(params, "parameter_index")

        track = self._require_track(track_index)
        device = self._require_device(track, track_index, device_index)
        parameter = self._require_parameter(device, track_index, device_index, parameter_index)
        self._set_parameter(
            parameter,
            value=params.get("value"),
            value_item=params.get("value_item"),
        )
        return self._ok(
            "parameter",
            {
                "track_index": track_index,
                "device_index": device_index,
                "parameter_index": parameter_index,
            },
            self._parameter_state(parameter, track_index, device_index, parameter_index),
        )

    def _cmd_nested_device_set_parameter(self, params):
        track_index = self._require_int(params, "track_index")
        parameter_index = self._require_int(params, "parameter_index")
        device_path = self._normalize_index_list(self._require_value(params, "device_path"), "device_path")
        chain_path = self._normalize_index_list(params.get("chain_path", []), "chain_path")
        chain_type_path = self._normalize_chain_types(params.get("chain_type_path", []))

        track = self._require_track(track_index)
        device = self._resolve_nested_device(track, device_path, chain_path, chain_type_path)
        parameter = self._require_parameter(device, track_index, device_path[-1], parameter_index)
        self._set_parameter(
            parameter,
            value=params.get("value"),
            value_item=params.get("value_item"),
        )
        return self._ok(
            "parameter",
            {
                "track_index": track_index,
                "device_path": device_path,
                "chain_path": chain_path,
                "chain_type_path": chain_type_path,
                "parameter_index": parameter_index,
            },
            self._parameter_state(
                parameter,
                track_index,
                device_path[-1],
                parameter_index,
                device_path=device_path,
                chain_path=chain_path,
                chain_type_path=chain_type_path,
            ),
        )

    def _cmd_device_delete(self, params):
        self._require_confirmed(params)
        track_index = self._require_int(params, "track_index")
        device_index = self._require_int(params, "device_index")
        track = self._require_track(track_index)
        self._require_device(track, track_index, device_index)
        track.delete_device(device_index)
        return self._ok("track", {"track_index": track_index}, self._track_state(track, track_index))

    def _song_state(self):
        selected_track_index = self._find_track_index(getattr(self._song.view, "selected_track", None))
        selected_scene_index = self._find_scene_index(getattr(self._song.view, "selected_scene", None))
        highlighted = self._find_highlighted_clip_slot()

        return {
            "name": getattr(self._song, "name", ""),
            "tempo": self._safe_number(getattr(self._song, "tempo", 120.0)),
            "is_playing": bool(getattr(self._song, "is_playing", False)),
            "metronome": bool(getattr(self._song, "metronome", False)),
            "current_song_time": self._safe_number(getattr(self._song, "current_song_time", 0.0)),
            "signature_numerator": int(getattr(self._song, "signature_numerator", 4)),
            "signature_denominator": int(getattr(self._song, "signature_denominator", 4)),
            "track_count": len(self._song.tracks),
            "scene_count": len(self._song.scenes),
            "selected_track_index": selected_track_index,
            "selected_scene_index": selected_scene_index,
            "highlighted_clip_slot": highlighted,
        }

    def _track_state(self, track, track_index):
        sends = []
        for send_index, send in enumerate(track.mixer_device.sends):
            sends.append(
                {
                    "send_index": send_index,
                    "name": getattr(send, "name", "Send {0}".format(send_index)),
                    "value": self._safe_number(getattr(send, "value", 0.0)),
                    "min": self._safe_number(getattr(send, "min", 0.0)),
                    "max": self._safe_number(getattr(send, "max", 1.0)),
                }
            )

        return {
            "track_index": track_index,
            "name": getattr(track, "name", ""),
            "color": getattr(track, "color", None),
            "is_midi_track": bool(getattr(track, "has_midi_input", False)),
            "is_audio_track": bool(getattr(track, "has_audio_input", False)),
            "can_be_armed": bool(getattr(track, "can_be_armed", False)),
            "arm": bool(getattr(track, "arm", False)),
            "mute": bool(getattr(track, "mute", False)),
            "solo": bool(getattr(track, "solo", False)),
            "is_foldable": bool(getattr(track, "is_foldable", False)),
            "is_grouped": bool(getattr(track, "is_grouped", False)),
            "playing_slot_index": int(getattr(track, "playing_slot_index", -1)),
            "fired_slot_index": int(getattr(track, "fired_slot_index", -1)),
            "volume": self._safe_number(track.mixer_device.volume.value),
            "pan": self._safe_number(track.mixer_device.panning.value),
            "sends": sends,
            "clip_slot_count": len(track.clip_slots),
            "device_count": len(track.devices),
            "input_routing_type": self._routing_name(getattr(track, "input_routing_type", None)),
            "output_routing_type": self._routing_name(getattr(track, "output_routing_type", None)),
        }

    def _scene_state(self, scene, scene_index):
        return {
            "scene_index": scene_index,
            "name": getattr(scene, "name", ""),
            "color": getattr(scene, "color", None),
            "is_empty": bool(getattr(scene, "is_empty", False)),
            "is_triggered": bool(getattr(scene, "is_triggered", False)),
            "tempo": getattr(scene, "tempo", None),
            "tempo_enabled": bool(getattr(scene, "tempo_enabled", False)),
            "time_signature_numerator": getattr(scene, "time_signature_numerator", None),
            "time_signature_denominator": getattr(scene, "time_signature_denominator", None),
            "time_signature_enabled": bool(getattr(scene, "time_signature_enabled", False)),
        }

    def _clip_slot_state(self, track, track_index, clip_slot, clip_slot_index):
        state = {
            "track_index": track_index,
            "clip_slot_index": clip_slot_index,
            "has_clip": bool(getattr(clip_slot, "has_clip", False)),
            "has_stop_button": bool(getattr(clip_slot, "has_stop_button", False)),
            "is_group_slot": bool(getattr(clip_slot, "is_group_slot", False)),
            "is_playing": bool(getattr(clip_slot, "is_playing", False)),
            "is_recording": bool(getattr(clip_slot, "is_recording", False)),
            "is_triggered": bool(getattr(clip_slot, "is_triggered", False)),
            "controls_other_clips": bool(getattr(clip_slot, "controls_other_clips", False)),
        }

        if clip_slot.has_clip:
            state["clip"] = self._clip_state(clip_slot.clip, track_index, clip_slot_index)
        else:
            state["clip"] = None

        return state

    def _clip_state(self, clip, track_index, clip_slot_index):
        return {
            "track_index": track_index,
            "clip_slot_index": clip_slot_index,
            "name": getattr(clip, "name", ""),
            "color": getattr(clip, "color", None),
            "length": self._safe_number(getattr(clip, "length", 0.0)),
            "is_audio_clip": bool(getattr(clip, "is_audio_clip", False)),
            "is_midi_clip": bool(getattr(clip, "is_midi_clip", False)),
            "is_playing": bool(getattr(clip, "is_playing", False)),
            "is_recording": bool(getattr(clip, "is_recording", False)),
            "is_triggered": bool(getattr(clip, "is_triggered", False)),
            "looping": bool(getattr(clip, "looping", False)),
            "loop_start": self._safe_number(getattr(clip, "loop_start", 0.0)),
            "loop_end": self._safe_number(getattr(clip, "loop_end", 0.0)),
            "start_marker": self._safe_number(getattr(clip, "start_marker", 0.0)),
            "end_marker": self._safe_number(getattr(clip, "end_marker", 0.0)),
        }

    def _device_state(
        self,
        device,
        track_index,
        device_index,
        device_path=None,
        chain_path=None,
        chain_type_path=None,
        include_parameters=False,
    ):
        state = {
            "track_index": track_index,
            "device_index": device_index,
            "device_path": list(device_path or [device_index]),
            "chain_path": list(chain_path or []),
            "chain_type_path": list(chain_type_path or []),
            "name": getattr(device, "name", ""),
            "class_name": getattr(device, "class_name", ""),
            "class_display_name": getattr(device, "class_display_name", ""),
            "type": self._device_type(device),
            "is_active": bool(getattr(device, "is_active", True)),
            "is_enabled": bool(getattr(device, "is_enabled", True)),
            "can_have_chains": bool(getattr(device, "can_have_chains", False)),
            "can_have_drum_pads": bool(getattr(device, "can_have_drum_pads", False)),
            "chain_count": len(getattr(device, "chains", [])),
            "return_chain_count": len(getattr(device, "return_chains", [])),
            "parameter_count": len(device.parameters),
        }

        if include_parameters:
            parameters = []
            for parameter_index, parameter in enumerate(device.parameters):
                parameters.append(
                    self._parameter_state(
                        parameter,
                        track_index,
                        device_index,
                        parameter_index,
                        device_path=device_path,
                        chain_path=chain_path,
                        chain_type_path=chain_type_path,
                    )
                )
            state["parameters"] = parameters

        return state

    def _parameter_state(
        self,
        parameter,
        track_index,
        device_index,
        parameter_index,
        device_path=None,
        chain_path=None,
        chain_type_path=None,
    ):
        value_items = list(getattr(parameter, "value_items", []) or [])
        return {
            "track_index": track_index,
            "device_index": device_index,
            "device_path": list(device_path or [device_index]),
            "chain_path": list(chain_path or []),
            "chain_type_path": list(chain_type_path or []),
            "parameter_index": parameter_index,
            "is_device_on_parameter": parameter_index == 0,
            "name": getattr(parameter, "name", ""),
            "original_name": getattr(parameter, "original_name", getattr(parameter, "name", "")),
            "value": self._safe_number(getattr(parameter, "value", 0.0)),
            "default_value": self._safe_number(getattr(parameter, "default_value", getattr(parameter, "value", 0.0))),
            "min": self._safe_number(getattr(parameter, "min", 0.0)),
            "max": self._safe_number(getattr(parameter, "max", 1.0)),
            "is_enabled": bool(getattr(parameter, "is_enabled", True)),
            "is_quantized": bool(getattr(parameter, "is_quantized", False)),
            "value_items": value_items,
        }

    def _device_tree(
        self,
        track_index,
        device,
        device_path,
        chain_path,
        chain_type_path,
        include_parameters,
        max_depth,
        depth,
    ):
        state = self._device_state(
            device,
            track_index,
            device_path[-1],
            device_path=device_path,
            chain_path=chain_path,
            chain_type_path=chain_type_path,
            include_parameters=include_parameters,
        )

        if depth >= max_depth:
            state["truncated"] = True
            state["chains"] = []
            state["return_chains"] = []
            return state

        state["chains"] = self._chain_collection_state(
            getattr(device, "chains", []),
            "chains",
            track_index,
            device_path,
            chain_path,
            chain_type_path,
            include_parameters,
            max_depth,
            depth,
        )
        state["return_chains"] = self._chain_collection_state(
            getattr(device, "return_chains", []),
            "return_chains",
            track_index,
            device_path,
            chain_path,
            chain_type_path,
            include_parameters,
            max_depth,
            depth,
        )
        return state

    def _chain_collection_state(
        self,
        chains,
        chain_type,
        track_index,
        parent_device_path,
        parent_chain_path,
        parent_chain_type_path,
        include_parameters,
        max_depth,
        depth,
    ):
        states = []
        for chain_index, chain in enumerate(chains):
            chain_state = {
                "chain_index": chain_index,
                "chain_type": chain_type,
                "name": getattr(chain, "name", ""),
                "color": getattr(chain, "color", None),
                "mute": bool(getattr(chain, "mute", False)),
                "solo": bool(getattr(chain, "solo", False)),
                "device_count": len(chain.devices),
                "devices": [],
            }

            child_chain_path = list(parent_chain_path) + [chain_index]
            child_chain_type_path = list(parent_chain_type_path) + [chain_type]
            for child_device_index, child_device in enumerate(chain.devices):
                child_device_path = list(parent_device_path) + [child_device_index]
                chain_state["devices"].append(
                    self._device_tree(
                        track_index,
                        child_device,
                        child_device_path,
                        child_chain_path,
                        child_chain_type_path,
                        include_parameters,
                        max_depth,
                        depth + 1,
                    )
                )

            states.append(chain_state)
        return states

    def _resolve_nested_device(self, track, device_path, chain_path, chain_type_path):
        if not device_path:
            raise AbletonMCPError("invalid_request", "device_path must contain at least one device index")

        if len(device_path) != len(chain_path) + 1:
            raise AbletonMCPError(
                "invalid_request",
                "device_path length must be exactly one greater than chain_path length",
            )

        if chain_type_path and len(chain_type_path) != len(chain_path):
            raise AbletonMCPError(
                "invalid_request",
                "chain_type_path length must match chain_path length",
            )

        if not chain_type_path:
            chain_type_path = ["chains"] * len(chain_path)

        device = self._require_device(track, None, device_path[0])
        for level, chain_index in enumerate(chain_path):
            chain_type = chain_type_path[level]
            if chain_type not in ("chains", "return_chains"):
                raise AbletonMCPError("invalid_request", "chain_type_path entries must be 'chains' or 'return_chains'")

            chain_collection = getattr(device, chain_type, None)
            if chain_collection is None:
                raise AbletonMCPError("unsupported_operation", "Device does not expose {0}".format(chain_type))

            if chain_index < 0 or chain_index >= len(chain_collection):
                raise AbletonMCPError("invalid_index", "Chain index out of range")

            chain = chain_collection[chain_index]
            next_device_index = device_path[level + 1]
            if next_device_index < 0 or next_device_index >= len(chain.devices):
                raise AbletonMCPError("invalid_index", "Nested device index out of range")

            device = chain.devices[next_device_index]

        return device

    def _normalize_index_list(self, value, field_name):
        if not isinstance(value, list):
            raise AbletonMCPError("invalid_request", "{0} must be a list of integers".format(field_name))
        try:
            return [int(item) for item in value]
        except Exception:
            raise AbletonMCPError("invalid_request", "{0} must be a list of integers".format(field_name))

    def _normalize_chain_types(self, value):
        if not value:
            return []
        if not isinstance(value, list):
            raise AbletonMCPError("invalid_request", "chain_type_path must be a list")
        return [str(item) for item in value]

    def _require_track(self, track_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise AbletonMCPError("invalid_index", "Track index out of range")
        return self._song.tracks[track_index]

    def _require_scene(self, scene_index):
        if scene_index < 0 or scene_index >= len(self._song.scenes):
            raise AbletonMCPError("invalid_index", "Scene index out of range")
        return self._song.scenes[scene_index]

    def _require_clip_slot(self, track, track_index, clip_slot_index):
        if clip_slot_index < 0 or clip_slot_index >= len(track.clip_slots):
            raise AbletonMCPError("invalid_index", "Clip slot index out of range")
        return track.clip_slots[clip_slot_index]

    def _require_clip(self, track, track_index, clip_slot_index):
        clip_slot = self._require_clip_slot(track, track_index, clip_slot_index)
        if not clip_slot.has_clip:
            raise AbletonMCPError("object_missing", "Clip slot does not contain a clip")
        return clip_slot.clip

    def _require_device(self, track, track_index, device_index):
        if device_index < 0 or device_index >= len(track.devices):
            raise AbletonMCPError("invalid_index", "Device index out of range")
        return track.devices[device_index]

    def _require_parameter(self, device, track_index, device_index, parameter_index):
        if parameter_index < 0 or parameter_index >= len(device.parameters):
            raise AbletonMCPError("invalid_index", "Parameter index out of range")
        return device.parameters[parameter_index]

    def _require_confirmed(self, params):
        if not bool(params.get("confirm_destructive", False)):
            raise AbletonMCPError(
                "destructive_action_not_confirmed",
                "Set confirm_destructive to true to perform this operation",
            )

    def _require_value(self, params, key):
        if key not in params:
            raise AbletonMCPError("invalid_request", "Missing required parameter: {0}".format(key))
        return params.get(key)

    def _require_int(self, params, key):
        return int(self._require_value(params, key))

    def _require_text(self, params, key):
        value = self._require_value(params, key)
        if value is None or value == "":
            raise AbletonMCPError("invalid_request", "{0} must not be empty".format(key))
        return value

    def _set_attr(self, target, attr_name, value, label):
        if not hasattr(target, attr_name):
            raise AbletonMCPError("unsupported_operation", "{0} is not available".format(label))
        setattr(target, attr_name, value)

    def _set_parameter(self, parameter, value=None, value_item=None):
        if value is None and value_item is None:
            raise AbletonMCPError("invalid_request", "Provide either value or value_item")

        if value is not None and value_item is not None:
            raise AbletonMCPError("invalid_request", "Provide only one of value or value_item")

        if value_item is not None:
            resolved_value = self._resolve_parameter_value_item(parameter, value_item)
        else:
            resolved_value = float(value)

        minimum = float(getattr(parameter, "min", resolved_value))
        maximum = float(getattr(parameter, "max", resolved_value))
        if resolved_value < minimum or resolved_value > maximum:
            raise AbletonMCPError(
                "invalid_request",
                "Value {0} is outside parameter range [{1}, {2}]".format(resolved_value, minimum, maximum),
            )
        parameter.value = resolved_value

    def _resolve_parameter_value_item(self, parameter, value_item):
        if value_item is None or str(value_item).strip() == "":
            raise AbletonMCPError("invalid_request", "value_item must not be empty")

        options = list(getattr(parameter, "value_items", []) or [])
        if not options:
            raise AbletonMCPError("unsupported_operation", "Parameter does not expose named value items")

        normalized_target = str(value_item).strip().lower()
        matched_index = None
        for index, option in enumerate(options):
            if str(option).strip().lower() == normalized_target:
                matched_index = index
                break

        if matched_index is None:
            raise AbletonMCPError(
                "invalid_request",
                "Unknown value_item '{0}'. Available options: {1}".format(value_item, ", ".join([str(item) for item in options])),
            )

        minimum = float(getattr(parameter, "min", 0.0))
        maximum = float(getattr(parameter, "max", float(len(options) - 1)))
        if len(options) == 1:
            return minimum

        step_count = float(len(options) - 1)
        span = maximum - minimum
        if span == step_count:
            return minimum + matched_index
        return minimum + (span * (float(matched_index) / step_count))

    def _find_track_index(self, track):
        if track is None:
            return None
        for index, candidate in enumerate(self._song.tracks):
            if candidate == track:
                return index
        return None

    def _find_scene_index(self, scene):
        if scene is None:
            return None
        for index, candidate in enumerate(self._song.scenes):
            if candidate == scene:
                return index
        return None

    def _find_highlighted_clip_slot(self):
        highlighted = getattr(self._song.view, "highlighted_clip_slot", None)
        if highlighted is None:
            return None

        for track_index, track in enumerate(self._song.tracks):
            for clip_slot_index, clip_slot in enumerate(track.clip_slots):
                if clip_slot == highlighted:
                    return {
                        "track_index": track_index,
                        "clip_slot_index": clip_slot_index,
                    }
        return None

    def _device_type(self, device):
        try:
            class_display_name = getattr(device, "class_display_name", "").lower()
            class_name = getattr(device, "class_name", "").lower()
            if getattr(device, "can_have_drum_pads", False):
                return "drum_machine"
            if getattr(device, "can_have_chains", False):
                return "rack"
            if "instrument" in class_display_name:
                return "instrument"
            if "audio_effect" in class_name:
                return "audio_effect"
            if "midi_effect" in class_name:
                return "midi_effect"
        except Exception:
            pass
        return "device"

    def _routing_name(self, routing):
        display_name = getattr(routing, "display_name", None)
        if display_name is not None:
            return display_name
        if isinstance(routing, dict):
            return routing.get("display_name")
        if hasattr(routing, "get"):
            try:
                return routing.get("display_name")
            except Exception:
                return None
        return None

    def _safe_number(self, value):
        try:
            return float(value)
        except Exception:
            return value
