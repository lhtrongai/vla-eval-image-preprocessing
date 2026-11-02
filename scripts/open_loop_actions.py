"""Open-loop action check: for the same observation, query the policy once per image pipeline (reference, the
reference again, jpeg_off, crop_off, bilinear, render224) and record the predicted actions; nothing but the reference
action is executed. --mode first: the first policy observation of every (task, initial state); --mode traj: every
--every-th query along the reference rollout. render224 uses a second env rendered at 224 and stepped with the same
actions. Output: OUT_DIR/actions_<model>_<mode>.jsonl (OpenVLA-7B: tokens, action, top-1 minus top-2 logit margin per
token; OpenVLA-OFT: the chunk of 8 actions) and, in traj mode, episodes_<model>_<mode>.jsonl.
Usage: OUT_DIR=... python open_loop_actions.py --model openvla7b|oft --mode first|traj [--states 0-49] [--every 1]
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import image_pipeline as ip  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", choices=["openvla7b", "oft"], required=True)
ap.add_argument("--mode", choices=["first", "traj"], required=True)
ap.add_argument("--states", default="0-49", help="initial states per task, e.g. 0-49 or 0-4")
ap.add_argument("--tasks", default="0-9")
ap.add_argument("--every", type=int, default=1, help="traj mode: compare variants at every k-th policy query")
args = ap.parse_args()
OUT_DIR = os.path.abspath(os.environ["OUT_DIR"])
os.makedirs(OUT_DIR, exist_ok=True)


def span(s):
    a, b = s.split("-") if "-" in s else (s, s)
    return list(range(int(a), int(b) + 1))


PIPES = ["reference", "reference_again", "jpeg_off", "crop_off", "bilinear", "render224"]
NUM_STEPS_WAIT, MAX_STEPS = 10, 220

if args.model == "openvla7b":
    ROOT = os.environ.get("OPENVLA_ROOT", "/workspace/openvla")
    sys.path.insert(0, ROOT)
    import transformers  # noqa: E402

    _orig = transformers.AutoModelForVision2Seq.from_pretrained

    def _with_sdpa(*a, **kw):  # the closed-loop OpenVLA-7B cells ran with sdpa attention (run_meta.json)
        kw["attn_implementation"] = "sdpa"
        return _orig(*a, **kw)

    transformers.AutoModelForVision2Seq.from_pretrained = _with_sdpa
    from experiments.robot.libero.libero_utils import get_libero_dummy_action, get_libero_env, resize_image  # noqa
    from experiments.robot.openvla_utils import get_processor, get_vla_action  # noqa: E402
    from experiments.robot.robot_utils import get_model, set_seed_everywhere  # noqa: E402

    class Cfg:
        model_family = "openvla"
        pretrained_checkpoint = "openvla/openvla-7b-finetuned-libero-spatial"
        load_in_8bit = False
        load_in_4bit = False
        center_crop = True
        unnorm_key = "libero_spatial"

    cfg = Cfg()
    set_seed_everywhere(7)
    model = get_model(cfg)
    processor = get_processor(cfg)
    if cfg.unnorm_key not in model.norm_stats and f"{cfg.unnorm_key}_no_noops" in model.norm_stats:
        cfg.unnorm_key += "_no_noops"
    capture = {}
    _generate = model.generate

    def _generate_with_scores(*a, **kw):  # same call as predict_action, also keeps the logits of every new token
        kw.update(output_scores=True, return_dict_in_generate=True)
        out = _generate(*a, **kw)
        capture["scores"] = [s[0].float().cpu().numpy() for s in out.scores]
        capture["ids"] = out.sequences[0, -len(out.scores):].cpu().numpy()
        return out.sequences

    model.generate = _generate_with_scores
    dummy = get_libero_dummy_action("openvla")
    stats = model.norm_stats[cfg.unnorm_key]["action"]

    def official_resize(raw):
        return resize_image(raw, (224, 224))

    def query(obs_raw, raw224, state, pipe, wrist=None, wrist224=None):
        img = {"jpeg_off": lambda: ip.resize_without_jpeg(obs_raw, 224),
               "bilinear": lambda: ip.resize_with_jpeg(obs_raw, 224, "bilinear"),
               "render224": lambda: official_resize(raw224)}.get(pipe, lambda: official_resize(obs_raw))()
        action = get_vla_action(model, processor, cfg.pretrained_checkpoint, {"full_image": img}, TASK_LABEL,
                                cfg.unnorm_key, center_crop=(pipe != "crop_off"))
        sc = capture["scores"]
        top2 = [np.sort(s)[-2:] for s in sc]
        return {"tokens": capture["ids"].tolist(), "action": np.asarray(action).tolist(),
                "margin": [float(t[1] - t[0]) for t in top2]}

    def make_env(task, res):
        return get_libero_env(task, "openvla", resolution=res)

    from experiments.robot.robot_utils import invert_gripper_action, normalize_gripper_action  # noqa: E402

    def step_action(rec):  # the official post-processing of an OpenVLA action before env.step
        a = normalize_gripper_action(np.asarray(rec["action"], dtype=float).copy(), binarize=True)
        return [invert_gripper_action(a)], 1
else:
    ROOT = os.environ.get("OFT_ROOT", "/workspace/openvla-oft")
    sys.path.insert(0, ROOT)
    import experiments.robot.libero.run_libero_eval as rle  # noqa: E402
    from experiments.robot.robot_utils import set_seed_everywhere  # noqa: E402

    cfg = rle.GenerateConfig(pretrained_checkpoint="moojink/openvla-7b-oft-finetuned-libero-spatial",
                             task_suite_name="libero_spatial", center_crop=True)
    rle.validate_config(cfg)
    set_seed_everywhere(cfg.seed)
    model, action_head, proprio_projector, noisy_action_projector, processor = rle.initialize_model(cfg)
    dummy = rle.get_libero_dummy_action(cfg.model_family)
    stats = model.norm_stats[cfg.unnorm_key]["action"]

    def resize_variant(img, pipe):
        if pipe == "jpeg_off":
            return ip.resize_without_jpeg(img, 224)
        if pipe == "bilinear":
            return ip.resize_with_jpeg(img, 224, "bilinear")
        return rle.resize_image_for_policy(img, 224)

    def query(obs, obs224, state, pipe):
        o = obs224 if pipe == "render224" else obs
        img, wrist = rle.get_libero_image(o), rle.get_libero_wrist_image(o)
        observation = {"full_image": resize_variant(img, pipe), "wrist_image": resize_variant(wrist, pipe),
                       "state": np.concatenate((o["robot0_eef_pos"], rle.quat2axisangle(o["robot0_eef_quat"]),
                                                o["robot0_gripper_qpos"]))}
        cfg.center_crop = pipe != "crop_off"
        actions = rle.get_action(cfg, model, observation, TASK_LABEL, processor=processor, action_head=action_head,
                                 proprio_projector=proprio_projector, noisy_action_projector=noisy_action_projector,
                                 use_film=cfg.use_film)
        cfg.center_crop = True
        return {"chunk": np.asarray(actions).tolist()}

    def make_env(task, res):
        return rle.get_libero_env(task, cfg.model_family, resolution=res)

    def step_action(rec):
        return [rle.process_action(np.asarray(a), cfg.model_family) for a in rec["chunk"]], len(rec["chunk"])

from libero.libero import benchmark  # noqa: E402

sys.path.insert(0, "/workspace/libero-vla-eval/scripts")
import episode_logging as el  # noqa: E402

suite = benchmark.get_benchmark_dict()["libero_spatial"]()
out_path = os.path.join(OUT_DIR, f"actions_{args.model}_{args.mode}.jsonl")
done = set()
if os.path.exists(out_path):
    for line in open(out_path):
        r = json.loads(line)
        done.add((r["task_id"], r["initial_state"], r["query_idx"]))
fh = open(out_path, "a")
ep_fh = open(os.path.join(OUT_DIR, f"episodes_{args.model}_{args.mode}.jsonl"), "a")
meta = {"argv": sys.argv, "model": args.model, "mode": args.mode, "pipelines": PIPES,
        "action_q01": np.asarray(stats["q01"]).tolist(), "action_q99": np.asarray(stats["q99"]).tolist(),
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S")}
json.dump(meta, open(os.path.join(OUT_DIR, f"meta_{args.model}_{args.mode}.json"), "w"), indent=1)

for task_id in span(args.tasks):
    task = suite.get_task(task_id)
    init_states = suite.get_task_init_states(task_id)
    env, TASK_LABEL = make_env(task, 256)
    env224, _ = make_env(task, 224)
    for s in span(args.states):
        if args.mode == "first" and (task_id, s, 0) in done:
            continue
        t0 = time.time()
        rng = np.random.get_state()  # fixture placement at reset draws from the global RNG: give env224 the same
        env.reset()                  # draw, and leave the RNG where a single-env run would leave it
        rng_after = np.random.get_state()
        np.random.set_state(rng)
        env224.reset()
        np.random.set_state(rng_after)
        obs, obs224 = env.set_init_state(init_states[s]), env224.set_init_state(init_states[s])
        same_fixtures = el.fixture_poses(env.env) == el.fixture_poses(env224.env)
        for _ in range(NUM_STEPS_WAIT):
            obs, _, _, _ = env.step(dummy)
            obs224, _, _, _ = env224.step(dummy)
        q, t, success, queue = 0, NUM_STEPS_WAIT, False, []
        while t < NUM_STEPS_WAIT + MAX_STEPS:
            if not queue:
                raw = obs["agentview_image"][::-1, ::-1]
                raw224 = obs224["agentview_image"][::-1, ::-1]
                ask = (lambda pipe: query(raw, raw224, None, pipe)) if args.model == "openvla7b" else \
                    (lambda pipe: query(obs, obs224, None, pipe))
                if q % args.every == 0 and (task_id, s, q) not in done:
                    res = {pipe: ask(pipe) for pipe in PIPES}
                    fh.write(json.dumps({"task_id": task_id, "initial_state": s, "query_idx": q, "env_step": t,
                                         "init_state_sha1": el.state_hash(init_states[s]),
                                         "same_fixtures_224": same_fixtures, "pred": res}) + "\n")
                    fh.flush()
                    ref = res["reference"]
                else:
                    ref = ask("reference")
                if args.mode == "first":
                    break
                queue, _ = step_action(ref)
                q += 1
            a = queue.pop(0)
            obs, _, done_flag, _ = env.step(np.asarray(a).tolist())
            obs224, _, _, _ = env224.step(np.asarray(a).tolist())
            t += 1
            if done_flag:
                success = True
                break
        if args.mode == "traj":  # the reference rollout should repeat the closed-loop reference episode
            ep_fh.write(json.dumps({"task_id": task_id, "initial_state": s, "success": success, "env_steps": t,
                                    "queries": q}) + "\n")
            ep_fh.flush()
        print(f"task {task_id} state {s}: {q} queries, success={success}, {time.time() - t0:.1f}s", flush=True)
    env.close()
    env224.close()
print("OPEN_LOOP_DONE", flush=True)
