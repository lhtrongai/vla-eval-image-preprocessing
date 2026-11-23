# Control pods log

Run commit: `e6ec1c2ee91cd246427c0a4a98a28a8ec0be2cd5` (plan commit `04fb502c2dd076ca8a66f645b78ca60d145efea2`).

## Evaluation pods (5)

| Label | Pod ID | CPU | Start (UTC) | Chain / Watchdog End (UTC) | Billed End (UTC) | Active Hours (to watchdog) | Billed Hours (total) | Outcome |
|---|---|---|---|---|---|---:|---:|---|
| `oft-controls` | `n4y72ojze627sl` | `AMD EPYC 7663 56-Core Processor` | 2026-11-22 18:15:34 UTC | 2026-11-22 22:16:55 UTC | ~2026-11-23 03:06:44 UTC | 4.0224 (241.35m) | 8.8527 (531.16m) | oft_spatial_rerun_stack_check rc=0 episodes=500; oft_spatial_sham_noise_seed1 rc=0 episodes=500; oft_spatial_sham_noise_seed2 rc=0 episodes=500; oft_spatial_sham_jpeg_q94 rc=0 episodes=500 (chain finished 22:15:18 UTC; watchdog runpodctl remove failed: API key not found; billed until balance exhaustion ~03:06:44 UTC) |
| `openvla7b-render224-cpu` | `ivbephacqutm5t` | `AMD EPYC 7663 56-Core Processor` | 2026-11-22 18:18:03 UTC | 2026-11-22 23:15:42 UTC | ~2026-11-23 03:06:44 UTC | 4.9607 (297.64m) | 8.8113 (528.68m) | openvla7b_spatial_render224_cpu_control rc=0 episodes=500 (chain finished 23:13:52 UTC; watchdog runpodctl remove failed: API key not found; billed until balance exhaustion ~03:06:44 UTC) |
| `openvla7b-jpeg-q94` | `vfhsjqyivuhbg4` | `AMD EPYC 7663 56-Core Processor` | 2026-11-22 18:26:20 UTC | 2026-11-22 23:33:40 UTC | ~2026-11-23 03:06:44 UTC | 5.1221 (307.32m) | 8.6732 (520.39m) | openvla7b_spatial_sham_jpeg_q94 rc=0 episodes=500 (chain finished 23:31:12 UTC; watchdog runpodctl remove failed: API key not found; billed until balance exhaustion ~03:06:44 UTC) |
| `openvla7b-noise-seed1` | `vjd8p17tv8lxc6` | `AMD EPYC 7663 56-Core Processor` | 2026-11-22 18:30:53 UTC | 2026-11-22 23:26:48 UTC | ~2026-11-23 03:06:44 UTC | 4.9319 (295.91m) | 8.5974 (515.85m) | openvla7b_spatial_sham_noise_seed1 rc=0 episodes=500 (chain finished 23:25:32 UTC; watchdog runpodctl remove failed: API key not found; billed until balance exhaustion ~03:06:44 UTC) |
| `openvla7b-noise-seed2` | `a91vxubp4g0xis` | `AMD EPYC 7663 56-Core Processor` | 2026-11-22 19:01:45 UTC | 2026-11-23 00:01:19 UTC | ~2026-11-23 03:06:44 UTC | 4.9926 (299.55m) | 8.0829 (484.97m) | openvla7b_spatial_sham_noise_seed2 rc=0 episodes=500 (chain finished 23:59:27 UTC; watchdog runpodctl remove failed: API key not found; billed until balance exhaustion ~03:06:44 UTC) |

## Packing pod (after all cells finished)

| Label | Pod ID | Type | Start (UTC) | End (UTC) | Billed Minutes | Billed GPU-Hours | Outcome |
|---|---|---|---|---|---:|---:|---|
| `pack-logs (CPU attempt 1)` | `y1rpho3yvochho` | `CPU pod (0 GPUs, $0.06/hr)` | 2026-11-23 10:33:55 UTC | 2026-11-23 10:38:38 UTC | 4.71 | 0.0000 | terminated (CPU pod could not mount GPU network volume ksvg8ptptr) |
| `pack-logs (CPU attempt 2)` | `ymzkwo1fxh5cht` | `CPU pod (0 GPUs, $0.06/hr)` | 2026-11-23 10:39:48 UTC | 2026-11-23 10:43:23 UTC | 3.58 | 0.0000 | terminated (CPU pod could not mount GPU network volume ksvg8ptptr) |
| `pack-logs` | `2l4bhuaepz5j40` | `Packing pod (1x RTX 4090, $0.89/hr)` | 2026-11-23 10:43:57 UTC | 2026-11-23 10:45:58 UTC | 2.02 | 0.0337 | pack_logs.sh exit 0 (90 files packed and verified; pod stopped and deleted) |

## Terminated / recycled pods (94 total: 85 wrong-CPU recycled, 9 pre-fix/SSH-setup terminated)

| Label | Pod ID | CPU | Start (UTC) | End (UTC) | Billed Minutes | Billed Hours | Outcome |
|---|---|---|---|---|---:|---:|---|
| `openvla7b-noise-seed1` | `ivqngl0t8gv3xf` | `not checked (SSH key ACL)` | 2026-11-22 17:54:05 UTC | 2026-11-22 17:55:36 UTC | 1.51 | 0.0251 | terminated before lscpu (SSH key ACL fix needed); 0 episodes |
| `openvla7b-noise-seed2` | `xr9vzjeji00460` | `not checked (SSH key ACL)` | 2026-11-22 17:54:18 UTC | 2026-11-22 17:55:38 UTC | 1.33 | 0.0222 | terminated before lscpu (SSH key ACL fix needed); 0 episodes |
| `openvla7b-jpeg-q94` | `isvhx9ufislxpj` | `not checked (SSH key ACL)` | 2026-11-22 17:54:21 UTC | 2026-11-22 17:55:40 UTC | 1.32 | 0.0219 | terminated before lscpu (SSH key ACL fix needed); 0 episodes |
| `openvla7b-render224-cpu` | `9msj8n6zz1kmwa` | `not checked (SSH key ACL)` | 2026-11-22 17:54:24 UTC | 2026-11-22 17:55:42 UTC | 1.30 | 0.0217 | terminated before lscpu (SSH key ACL fix needed); 0 episodes |
| `oft-controls` | `yln068cdcljp3b` | `not checked (SSH key ACL)` | 2026-11-22 17:54:27 UTC | 2026-11-22 17:55:44 UTC | 1.28 | 0.0214 | terminated before lscpu (SSH key ACL fix needed); 0 episodes |
| `openvla7b-noise-seed1` | `zj7vz0qg32ktov` | `AMD EPYC 7663 56-Core Processor` | 2026-11-22 17:59:01 UTC | 2026-11-22 18:06:05 UTC | 7.07 | 0.1178 | terminated before setup (04fb502 nvidia-smi name truncation); 0 episodes |
| `openvla7b-noise-seed2` | `vxyub5q3qnbxkx` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 17:59:03 UTC | 2026-11-22 18:00:35 UTC | 1.53 | 0.0255 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `dalnqg4126sr25` | `AMD EPYC 7713P 64-Core Processor` | 2026-11-22 17:59:05 UTC | 2026-11-22 18:00:09 UTC | 1.06 | 0.0176 | terminated (wrong CPU); 0 episodes |
| `openvla7b-render224-cpu` | `sd8i080fmd5hm0` | `AMD EPYC-Milan Processor` | 2026-11-22 17:59:07 UTC | 2026-11-22 18:00:15 UTC | 1.13 | 0.0189 | terminated (wrong CPU); 0 episodes |
| `oft-controls` | `2gxw931rbfzh0q` | `AMD EPYC 7663 56-Core Processor` | 2026-11-22 17:59:09 UTC | 2026-11-22 18:06:06 UTC | 6.95 | 0.1158 | terminated before setup (04fb502 nvidia-smi name truncation); 0 episodes |
| `openvla7b-noise-seed2` | `2pkhspkq6rwkw9` | `AMD EPYC 7713 64-Core Processor` | 2026-11-22 18:00:48 UTC | 2026-11-22 18:01:47 UTC | 0.99 | 0.0164 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `lc5ngl7zn5i1dc` | `not checked (pre-fix stop)` | 2026-11-22 18:00:51 UTC | 2026-11-22 18:06:07 UTC | 5.27 | 0.0878 | terminated before setup (04fb502 nvidia-smi name truncation); 0 episodes |
| `openvla7b-render224-cpu` | `m61inowo8i6adn` | `not checked (pre-fix stop)` | 2026-11-22 18:00:54 UTC | 2026-11-22 18:06:08 UTC | 5.23 | 0.0872 | terminated before setup (04fb502 nvidia-smi name truncation); 0 episodes |
| `openvla7b-noise-seed2` | `c4r5fkk8ra16vi` | `AMD EPYC 7443P 24-Core Processor` | 2026-11-22 18:15:33 UTC | 2026-11-22 18:15:49 UTC | 0.27 | 0.0046 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed1` | `sg2k2yyw7ideuo` | `AMD EPYC 7713 64-Core Processor` | 2026-11-22 18:15:33 UTC | 2026-11-22 18:16:13 UTC | 0.66 | 0.0110 | terminated (wrong CPU); 0 episodes |
| `openvla7b-render224-cpu` | `81tsvovgzqe9is` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:15:33 UTC | 2026-11-22 18:16:01 UTC | 0.46 | 0.0077 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `5sjq49p82qcgpe` | `AMD EPYC 7443P 24-Core Processor` | 2026-11-22 18:15:51 UTC | 2026-11-22 18:16:19 UTC | 0.46 | 0.0076 | terminated (wrong CPU); 0 episodes |
| `openvla7b-render224-cpu` | `wmtsy2ks269tmt` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:16:03 UTC | 2026-11-22 18:16:42 UTC | 0.65 | 0.0108 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `gt4a4j3i668j72` | `AMD EPYC 7443P 24-Core Processor` | 2026-11-22 18:16:08 UTC | 2026-11-22 18:16:49 UTC | 0.68 | 0.0113 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed1` | `iqw0l4csx34jia` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:16:15 UTC | 2026-11-22 18:17:06 UTC | 0.85 | 0.0142 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `pxuxnopwvf9xw2` | `AMD EPYC 7443P 24-Core Processor` | 2026-11-22 18:16:21 UTC | 2026-11-22 18:16:49 UTC | 0.46 | 0.0077 | terminated (wrong CPU); 0 episodes |
| `openvla7b-render224-cpu` | `ij5h9siukuq2n8` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:16:44 UTC | 2026-11-22 18:17:00 UTC | 0.27 | 0.0044 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `uqerdoz8b0juou` | `AMD EPYC 7713P 64-Core Processor` | 2026-11-22 18:16:51 UTC | 2026-11-22 18:17:19 UTC | 0.47 | 0.0078 | terminated (wrong CPU); 0 episodes |
| `openvla7b-render224-cpu` | `273xpkmbus3stn` | `AMD EPYC 7443P 24-Core Processor` | 2026-11-22 18:17:03 UTC | 2026-11-22 18:17:41 UTC | 0.65 | 0.0108 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed1` | `om0xytrs50dqq6` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:17:08 UTC | 2026-11-22 18:17:36 UTC | 0.46 | 0.0077 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `9kx9mu3l3w9g9w` | `AMD EPYC 7713P 64-Core Processor` | 2026-11-22 18:17:21 UTC | 2026-11-22 18:17:49 UTC | 0.46 | 0.0077 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed1` | `wq2nw3ejy7lwr9` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:17:38 UTC | 2026-11-22 18:18:08 UTC | 0.50 | 0.0083 | terminated (wrong CPU); 0 episodes |
| `openvla7b-render224-cpu` | `xj82embok5y62z` | `AMD EPYC 7443P 24-Core Processor` | 2026-11-22 18:17:43 UTC | 2026-11-22 18:18:00 UTC | 0.27 | 0.0045 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `afcu3q72nuut1z` | `AMD EPYC 7713P 64-Core Processor` | 2026-11-22 18:17:51 UTC | 2026-11-22 18:18:19 UTC | 0.47 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed1` | `mfomq99t94tcev` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:18:10 UTC | 2026-11-22 18:18:38 UTC | 0.46 | 0.0076 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `viona5i4273vri` | `AMD EPYC 7713P 64-Core Processor` | 2026-11-22 18:18:22 UTC | 2026-11-22 18:18:40 UTC | 0.29 | 0.0048 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed1` | `jvpw43ma7c949o` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:18:40 UTC | 2026-11-22 18:19:08 UTC | 0.47 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `dkglftyfi9emwf` | `AMD EPYC 7713P 64-Core Processor` | 2026-11-22 18:18:42 UTC | 2026-11-22 18:19:09 UTC | 0.46 | 0.0076 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed1` | `kbvpb7oza884zm` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:19:10 UTC | 2026-11-22 18:19:38 UTC | 0.46 | 0.0076 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `djenfrldi8jy8t` | `AMD EPYC 7713P 64-Core Processor` | 2026-11-22 18:19:11 UTC | 2026-11-22 18:19:39 UTC | 0.46 | 0.0077 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed1` | `jucnora3hkcd7d` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:19:40 UTC | 2026-11-22 18:20:10 UTC | 0.51 | 0.0085 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `pdo45uk8e7dqw0` | `AMD EPYC 7713P 64-Core Processor` | 2026-11-22 18:19:41 UTC | 2026-11-22 18:20:11 UTC | 0.50 | 0.0083 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed1` | `nsd7mr96yiw0e8` | `AMD EPYC 7713P 64-Core Processor` | 2026-11-22 18:20:13 UTC | 2026-11-22 18:20:41 UTC | 0.48 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `cw8wvwvmz6ioqe` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:20:13 UTC | 2026-11-22 18:20:41 UTC | 0.46 | 0.0077 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `k2f25mtg5x72lv` | `AMD EPYC-Milan Processor` | 2026-11-22 18:20:43 UTC | 2026-11-22 18:21:00 UTC | 0.28 | 0.0047 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `jxogz1ggh5nqbu` | `AMD EPYC-Milan Processor` | 2026-11-22 18:21:03 UTC | 2026-11-22 18:21:42 UTC | 0.65 | 0.0109 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `qd4qdjay96d3if` | `AMD EPYC-Milan Processor` | 2026-11-22 18:21:44 UTC | 2026-11-22 18:22:12 UTC | 0.47 | 0.0078 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `3laygqinbr0fia` | `AMD EPYC-Milan Processor` | 2026-11-22 18:22:14 UTC | 2026-11-22 18:22:42 UTC | 0.47 | 0.0078 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `dvvb687n505emh` | `AMD EPYC-Milan Processor` | 2026-11-22 18:22:45 UTC | 2026-11-22 18:23:13 UTC | 0.47 | 0.0078 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `zd2ap65cm26juy` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:23:15 UTC | 2026-11-22 18:23:43 UTC | 0.47 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `fizz5rpvc6ysgx` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:23:46 UTC | 2026-11-22 18:24:14 UTC | 0.47 | 0.0078 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `dacrt8eb55o7re` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:24:16 UTC | 2026-11-22 18:24:43 UTC | 0.46 | 0.0076 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `2b817mt7b4xszo` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:24:45 UTC | 2026-11-22 18:25:15 UTC | 0.49 | 0.0081 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `xlu0gl8ueqwsbr` | `AMD EPYC 7713 64-Core Processor` | 2026-11-22 18:25:17 UTC | 2026-11-22 18:25:35 UTC | 0.29 | 0.0049 | terminated (wrong CPU); 0 episodes |
| `openvla7b-jpeg-q94` | `khfqfn7au0vhi1` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:25:37 UTC | 2026-11-22 18:26:18 UTC | 0.67 | 0.0111 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `f1lt2fv7z2sktn` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:28:31 UTC | 2026-11-22 18:29:01 UTC | 0.49 | 0.0082 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `966x9sy693pivg` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:29:04 UTC | 2026-11-22 18:29:21 UTC | 0.29 | 0.0048 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `vlpphte4gik0yd` | `AMD EPYC-Milan Processor` | 2026-11-22 18:29:25 UTC | 2026-11-22 18:29:54 UTC | 0.48 | 0.0081 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `euzui8x905qhp1` | `AMD EPYC-Milan Processor` | 2026-11-22 18:29:56 UTC | 2026-11-22 18:30:26 UTC | 0.50 | 0.0083 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `rk8synjvw9uyuk` | `AMD EPYC-Milan Processor` | 2026-11-22 18:30:28 UTC | 2026-11-22 18:30:46 UTC | 0.29 | 0.0049 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `24ow3llt4fs1kk` | `AMD EPYC-Milan Processor` | 2026-11-22 18:30:48 UTC | 2026-11-22 18:31:19 UTC | 0.52 | 0.0087 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `rtkwt3nsebalvk` | `AMD EPYC-Milan Processor` | 2026-11-22 18:31:22 UTC | 2026-11-22 18:31:50 UTC | 0.48 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `ybjgmteg2caedd` | `AMD EPYC-Milan Processor` | 2026-11-22 18:31:53 UTC | 2026-11-22 18:32:22 UTC | 0.47 | 0.0078 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `cxn6du7tbs7e0j` | `AMD EPYC-Milan Processor` | 2026-11-22 18:32:24 UTC | 2026-11-22 18:32:41 UTC | 0.28 | 0.0047 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `72r94jrsq9c53c` | `AMD EPYC-Milan Processor` | 2026-11-22 18:32:43 UTC | 2026-11-22 18:33:12 UTC | 0.49 | 0.0081 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `xu0efln866f1ka` | `AMD EPYC-Milan Processor` | 2026-11-22 18:33:14 UTC | 2026-11-22 18:33:44 UTC | 0.49 | 0.0082 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `kjnd6hwszv970b` | `AMD EPYC-Milan Processor` | 2026-11-22 18:33:46 UTC | 2026-11-22 18:34:52 UTC | 1.09 | 0.0182 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `cuqo2bobzxsb1c` | `AMD EPYC-Milan Processor` | 2026-11-22 18:34:54 UTC | 2026-11-22 18:35:23 UTC | 0.48 | 0.0080 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `xgt363v187nxe7` | `AMD EPYC-Milan Processor` | 2026-11-22 18:35:26 UTC | 2026-11-22 18:35:54 UTC | 0.47 | 0.0078 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `2f4y7aod1r1udv` | `AMD EPYC-Milan Processor` | 2026-11-22 18:35:56 UTC | 2026-11-22 18:36:26 UTC | 0.49 | 0.0082 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `y6uc43dnoqeynr` | `AMD EPYC-Milan Processor` | 2026-11-22 18:36:28 UTC | 2026-11-22 18:36:45 UTC | 0.28 | 0.0046 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `xnpq2lv7q6rfkr` | `AMD EPYC-Milan Processor` | 2026-11-22 18:36:47 UTC | 2026-11-22 18:37:15 UTC | 0.46 | 0.0077 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `5mzn23ey046oas` | `AMD EPYC-Milan Processor` | 2026-11-22 18:37:18 UTC | 2026-11-22 18:37:46 UTC | 0.47 | 0.0078 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `8w5yjse8cf7bl0` | `AMD EPYC-Milan Processor` | 2026-11-22 18:37:48 UTC | 2026-11-22 18:38:17 UTC | 0.47 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `00xh82846at2bk` | `AMD EPYC-Milan Processor` | 2026-11-22 18:38:19 UTC | 2026-11-22 18:38:59 UTC | 0.67 | 0.0112 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `r9l2i74ht8zwq1` | `AMD EPYC-Milan Processor` | 2026-11-22 18:39:02 UTC | 2026-11-22 18:39:19 UTC | 0.29 | 0.0048 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `rqdfe2en6li4cc` | `AMD EPYC-Milan Processor` | 2026-11-22 18:39:21 UTC | 2026-11-22 18:40:02 UTC | 0.68 | 0.0114 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `6mqe0u2f9l6oy4` | `AMD EPYC-Milan Processor` | 2026-11-22 18:40:07 UTC | 2026-11-22 18:40:38 UTC | 0.52 | 0.0086 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `zg93glmbphi0dz` | `AMD EPYC-Milan Processor` | 2026-11-22 18:40:41 UTC | 2026-11-22 18:41:09 UTC | 0.47 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `99zm8zyfvtkzwv` | `AMD EPYC-Milan Processor` | 2026-11-22 18:41:11 UTC | 2026-11-22 18:41:40 UTC | 0.47 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `br100io5hzn3b3` | `AMD EPYC-Milan Processor` | 2026-11-22 18:41:42 UTC | 2026-11-22 18:42:11 UTC | 0.49 | 0.0082 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `dshsdsxpt4ztk2` | `AMD EPYC-Milan Processor` | 2026-11-22 18:42:13 UTC | 2026-11-22 18:42:30 UTC | 0.28 | 0.0046 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `p5srsmxlpqoidn` | `AMD EPYC 7443P 24-Core Processor` | 2026-11-22 18:52:47 UTC | 2026-11-22 18:53:16 UTC | 0.49 | 0.0081 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `el8s0ynml9dexg` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:53:19 UTC | 2026-11-22 18:53:36 UTC | 0.29 | 0.0048 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `vl6ze37gsq5nrm` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:53:39 UTC | 2026-11-22 18:54:08 UTC | 0.49 | 0.0082 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `lm8c1ba2swzrmw` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:54:11 UTC | 2026-11-22 18:54:53 UTC | 0.70 | 0.0117 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `e9jqp18yeq14o3` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:54:56 UTC | 2026-11-22 18:55:24 UTC | 0.48 | 0.0080 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `h6dsrzsqe320l2` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:55:27 UTC | 2026-11-22 18:55:55 UTC | 0.47 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `ysrxuu440sw66b` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:55:58 UTC | 2026-11-22 18:56:25 UTC | 0.46 | 0.0077 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `a95mat6esbz0aa` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:56:28 UTC | 2026-11-22 18:56:56 UTC | 0.47 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `flwo9vev1j3sx9` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:56:58 UTC | 2026-11-22 18:57:16 UTC | 0.29 | 0.0048 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `1bwdj10dkk5wiq` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:57:18 UTC | 2026-11-22 18:57:46 UTC | 0.47 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `r43ugc4eroj198` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:57:49 UTC | 2026-11-22 18:58:28 UTC | 0.66 | 0.0110 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `4xtew0wb95clk7` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:58:31 UTC | 2026-11-22 18:58:59 UTC | 0.47 | 0.0079 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `g52k1nbddoqitu` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:59:01 UTC | 2026-11-22 18:59:30 UTC | 0.48 | 0.0080 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `3i88d5ltgkxrho` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 18:59:34 UTC | 2026-11-22 19:00:19 UTC | 0.75 | 0.0124 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `0ezt5mobcxnout` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 19:00:22 UTC | 2026-11-22 19:00:40 UTC | 0.30 | 0.0050 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `6zj68exl4gssj0` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 19:00:42 UTC | 2026-11-22 19:01:00 UTC | 0.29 | 0.0049 | terminated (wrong CPU); 0 episodes |
| `openvla7b-noise-seed2` | `qval88jyu7ca4f` | `AMD EPYC 7443 24-Core Processor` | 2026-11-22 19:01:02 UTC | 2026-11-22 19:01:40 UTC | 0.63 | 0.0105 | terminated (wrong CPU); 0 episodes |

## GPU-hour and cost summary

- **Active evaluation pod time (5 pods, creation to watchdog removal attempt):** `24.0297` GPU-hours (`1441.78` minutes)
- **Recycled / pre-fix terminated pods (94 pods):** `1.2467` GPU-hours (`74.80` minutes: `0.7257` GPU-hours across 85 wrong-CPU pods, `0.5209` GPU-hours across 9 pre-fix/SSH-setup pods)
- **Packing pod (`2l4bhuaepz5j40`):** `0.0337` GPU-hours (`2.02` minutes)
- **Subtotal active GPU-hours (setup, checks, evaluation, recycling, packing):** **`25.3100` GPU-hours** (within the 30 GPU-hour budget)
- **Post-watchdog idle billed time (5 evaluation pods after `runpodctl remove pod` inside the containers failed with `Error: API key not found`, until account balance exhaustion at `~2026-11-23 03:06:44 UTC`):** `18.9878` GPU-hours (`1139.27` minutes)
- **Total billed GPU-hours (including post-watchdog idle time):** **`44.2978` GPU-hours**
- **Total cost billed on RunPod:** **`$32.28`** (`$32.2207` initial balance down to `-$0.0278`, plus `$0.0281` after `$10.00` top-up; ending balance `$9.9441`; includes `~$31.93` pod compute/disk and `~$0.35` network volume storage at `$0.019/hr`).
