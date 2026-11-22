# Independent recheck of the paper numbers

numpy 2.5.3, scipy 1.18.1, Python 3.13.18

## Data checks

- Initial-state hashes against the OpenVLA-7B reference cell: openvla7b_spatial_reference 500/500, openvla7b_spatial_rerun 500/500, openvla7b_spatial_jpeg_off 500/500, openvla7b_spatial_crop_off 500/500, openvla7b_spatial_bilinear 500/500, openvla7b_spatial_render224 500/500, oft_spatial_reference no hashes logged, oft_spatial_rerun 500/500, oft_spatial_jpeg_off 500/500, oft_spatial_crop_off 500/500, oft_spatial_bilinear 500/500, oft_spatial_render224 500/500, oft_spatial_crop_off_cpu_control 500/500
- OpenVLA-OFT reference: the original script logs carry no hash; its pairs are keyed by task line and episode counter (states 20-49: counter + 20). The rerun repeats all 500 outcomes of it, including the 5 failures.
- Problems found by the loaders: 0

## Closed loop against the reference cell

| Cell | Success | Wilson 95% | Diff | Exact boot 95% | MC boot 95% (100 seeds) | UB loss | Lost/gained | McNemar p | Holm p | Band |
|---|---|---|---|---|---|---|---|---|---|---|
| openvla7b_spatial_rerun | 424/500 | [81.4, 87.7] | -0.2 | [-1.0*, +0.4] | lo -1.0/-0.8, hi +0.4 | 0.8 (0.8) | 2/1 | 1 | nan | 0.68 |
| openvla7b_spatial_jpeg_off | 421/500 | [80.7, 87.1] | -0.8 | [-4.2*, +2.6*] | lo -4.2/-4.0, hi +2.4/+2.6 | 3.6 (3.6) | 39/35 | 0.7275 | nan | 3.37 |
| openvla7b_spatial_crop_off | 420/500 | [80.5, 87.0] | -1.0 | [-4.6*, +2.6*] | lo -4.6/-4.4, hi +2.4/+2.6 | 4.0* (3.8/4.0) | 43/38 | 0.657 | 1 | 3.53 |
| openvla7b_spatial_bilinear | 414/500 | [79.2, 85.9] | -2.2 | [-5.8*, +1.4*] | lo -5.8/-5.6, hi +1.2/+1.4 | 5.2 (5.2) | 47/36 | 0.2723 | 1 | 3.57 |
| openvla7b_spatial_render224 | 427/500 | [82.0, 88.2] | +0.4 | [-3.4*, +4.2*] | lo -3.4/-3.2, hi +4.0/+4.2 | 2.8* (2.6/2.8) | 45/47 | 0.917 | 1 | 3.76 |
| oft_spatial_rerun | 495/500 | [97.7, 99.6] | +0.0 | [+0.0, +0.0] | lo +0.0, hi +0.0 | 0.0 (0.0) | 0/0 | 1 | nan | 0.00 |
| oft_spatial_jpeg_off | 491/500 | [96.6, 99.1] | -0.8 | [-2.0*, +0.4] | lo -2.2/-2.0, hi +0.4 | 1.8 (1.8) | 7/3 | 0.3438 | 1 | 1.24 |
| oft_spatial_crop_off | 483/500 | [94.6, 97.9] | -2.4 | [-4.2*, -0.8] | lo -4.2/-4.0, hi -0.8 | 3.8 (3.8) | 15/3 | 0.007538 | 0.05276 | 1.66 |
| oft_spatial_bilinear | 496/500 | [98.0, 99.7] | +0.2 | [-0.8, +1.2] | lo -0.8, hi +1.2 | 0.6 (0.6) | 3/4 | 1 | 1 | 1.04 |
| oft_spatial_render224 | 491/500 | [96.6, 99.1] | -0.8 | [-2.0*, +0.4] | lo -2.2/-2.0, hi +0.4 | 1.8 (1.8) | 7/3 | 0.3438 | 1 | 1.24 |
| oft_spatial_crop_off_cpu_control | 483/500 | [94.6, 97.9] | -2.4 | [-4.2*, -0.8] | lo -4.2/-4.0, hi -0.8 | 3.8 (3.8) | 15/3 | 0.007538 | nan | 1.66 |

`*`: edge, the exact cumulative probability is within 0.004 of the target quantile, so the Monte Carlo value depends on the seed.

## Open loop: flips implied by the summary against the closed-loop cells

| Model, step | First actions changed | Flips implied | Closed-loop flips |
|---|---|---|---|
| openvla7b jpeg_off | 144 | 74 | 74 |
| openvla7b crop_off | 477 | 81 | 81 |
| openvla7b bilinear | 270 | 83 | 83 |
| openvla7b render224 | 390 | 92 | 92 |
| oft jpeg_off | 493 | 10 | 10 |
| oft crop_off | 500 | 18 | 18 |
| oft bilinear | 500 | 7 | 7 |
| oft render224 | 500 | 10 | 10 |

## Pilot

| Pilot cell | Started | JPEG | Center crop | Differs from the full cell on states 0-19 |
|---|---|---|---|---|
| oft_jpeg_off | 2026-10-12 06:28:07 | off | True | 0 |
| oft_reference | 2026-10-12 01:55:49 | on | True | 0 |
| oft_rerun | 2026-10-12 06:52:01 | on | True | 0 |
| openvla_crop_off | 2026-10-12 07:15:47 | on | False | 1 |
| openvla_jpeg_off | 2026-10-12 04:26:57 | off | True | 0 |
| openvla_reference | 2026-10-12 02:20:07 | on | True | 0 |
| openvla_rerun | 2026-10-12 09:21:14 | on | True | 0 |

## Every macro compared

| Macro | numbers.tex | Recomputed | Result | Note |
|---|---|---|---|---|
| SevRefK | 425 | 425 | match |  |
| SevRefPct | 85.0 | 85.0 | match |  |
| SevRefLo | 81.6 | 81.6 | match |  |
| SevRefHi | 87.9 | 87.9 | match |  |
| SevRerunK | 424 | 424 | match |  |
| SevRerunPct | 84.8 | 84.8 | match |  |
| SevRerunDiff | -0.2 | -0.2 | match |  |
| SevRerunLo | -1.0 | -1.0 | match | edge; 20,000 draws give -1.0 or -0.8 |
| SevRerunHi | +0.4 | +0.4 | match |  |
| SevRerunUB | 0.8 | 0.8 | match |  |
| SevRerunLost | 2 | 2 | match |  |
| SevRerunGained | 1 | 1 | match |  |
| SevRerunFlips | 3 | 3 | match |  |
| SevRerunP | 1.00 | 1.00 | match |  |
| SevRerunBand | 0.7 | 0.7 | match |  |
| SevRerunFlipPct | 0.6 | 0.6 | match |  |
| SevJpegK | 421 | 421 | match |  |
| SevJpegPct | 84.2 | 84.2 | match |  |
| SevJpegDiff | -0.8 | -0.8 | match |  |
| SevJpegLo | -4.2 | -4.2 | match | edge; 20,000 draws give -4.2 or -4.0 |
| SevJpegHi | +2.6 | +2.6 | match | edge; 20,000 draws give +2.4 or +2.6 |
| SevJpegUB | 3.6 | 3.6 | match |  |
| SevJpegLost | 39 | 39 | match |  |
| SevJpegGained | 35 | 35 | match |  |
| SevJpegFlips | 74 | 74 | match |  |
| SevJpegP | 0.73 | 0.73 | match |  |
| SevJpegBand | 3.4 | 3.4 | match |  |
| SevJpegFlipPct | 14.8 | 14.8 | match |  |
| SevCropK | 420 | 420 | match |  |
| SevCropPct | 84.0 | 84.0 | match |  |
| SevCropDiff | -1.0 | -1.0 | match |  |
| SevCropLo | -4.6 | -4.6 | match | edge; 20,000 draws give -4.6 or -4.4 |
| SevCropHi | +2.6 | +2.6 | match | edge; 20,000 draws give +2.4 or +2.6 |
| SevCropUB | 4.0 | 4.0 | match | edge; 20,000 draws give 3.8 or 4.0 |
| SevCropLost | 43 | 43 | match |  |
| SevCropGained | 38 | 38 | match |  |
| SevCropFlips | 81 | 81 | match |  |
| SevCropP | 0.66 | 0.66 | match |  |
| SevCropBand | 3.5 | 3.5 | match |  |
| SevCropFlipPct | 16.2 | 16.2 | match |  |
| SevCropHolm | 1.00 | 1.00 | match |  |
| SevBilK | 414 | 414 | match |  |
| SevBilPct | 82.8 | 82.8 | match |  |
| SevBilDiff | -2.2 | -2.2 | match |  |
| SevBilLo | -5.8 | -5.8 | match | edge; 20,000 draws give -5.8 or -5.6 |
| SevBilHi | +1.4 | +1.4 | match | edge; 20,000 draws give +1.2 or +1.4 |
| SevBilUB | 5.2 | 5.2 | match |  |
| SevBilLost | 47 | 47 | match |  |
| SevBilGained | 36 | 36 | match |  |
| SevBilFlips | 83 | 83 | match |  |
| SevBilP | 0.27 | 0.27 | match |  |
| SevBilBand | 3.6 | 3.6 | match |  |
| SevBilFlipPct | 16.6 | 16.6 | match |  |
| SevBilHolm | 1.00 | 1.00 | match |  |
| SevRendK | 427 | 427 | match |  |
| SevRendPct | 85.4 | 85.4 | match |  |
| SevRendDiff | +0.4 | +0.4 | match |  |
| SevRendLo | -3.4 | -3.4 | match | edge; 20,000 draws give -3.4 or -3.2 |
| SevRendHi | +4.2 | +4.2 | match | edge; 20,000 draws give +4.0 or +4.2 |
| SevRendUB | 2.8 | 2.8 | match | edge; 20,000 draws give 2.6 or 2.8 |
| SevRendLost | 45 | 45 | match |  |
| SevRendGained | 47 | 47 | match |  |
| SevRendFlips | 92 | 92 | match |  |
| SevRendP | 0.92 | 0.92 | match |  |
| SevRendBand | 3.8 | 3.8 | match |  |
| SevRendFlipPct | 18.4 | 18.4 | match |  |
| SevRendHolm | 1.00 | 1.00 | match |  |
| SevFlipsMin | 74 | 74 | match |  |
| SevFlipsMax | 92 | 92 | match |  |
| SevBandMin | 3.4 | 3.4 | match |  |
| SevBandMax | 3.8 | 3.8 | match |  |
| SevVarMinPct | 82.8 | 82.8 | match |  |
| SevVarMaxPct | 85.4 | 85.4 | match |  |
| OftRefK | 495 | 495 | match |  |
| OftRefPct | 99.0 | 99.0 | match |  |
| OftRefLo | 97.7 | 97.7 | match |  |
| OftRefHi | 99.6 | 99.6 | match |  |
| OftRerunK | 495 | 495 | match |  |
| OftRerunPct | 99.0 | 99.0 | match |  |
| OftRerunDiff | 0.0 | 0.0 | match |  |
| OftRerunLo | 0.0 | 0.0 | match |  |
| OftRerunHi | 0.0 | 0.0 | match |  |
| OftRerunUB | 0.0 | 0.0 | match |  |
| OftRerunLost | 0 | 0 | match |  |
| OftRerunGained | 0 | 0 | match |  |
| OftRerunFlips | 0 | 0 | match |  |
| OftRerunP | 1.00 | 1.00 | match |  |
| OftRerunBand | 0.0 | 0.0 | match |  |
| OftRerunFlipPct | 0.0 | 0.0 | match |  |
| OftJpegK | 491 | 491 | match |  |
| OftJpegPct | 98.2 | 98.2 | match |  |
| OftJpegDiff | -0.8 | -0.8 | match |  |
| OftJpegLo | -2.0 | -2.0 | match | edge; 20,000 draws give -2.2 or -2.0 |
| OftJpegHi | +0.4 | +0.4 | match |  |
| OftJpegUB | 1.8 | 1.8 | match |  |
| OftJpegLost | 7 | 7 | match |  |
| OftJpegGained | 3 | 3 | match |  |
| OftJpegFlips | 10 | 10 | match |  |
| OftJpegP | 0.34 | 0.34 | match |  |
| OftJpegBand | 1.2 | 1.2 | match |  |
| OftJpegFlipPct | 2.0 | 2.0 | match |  |
| OftJpegHolm | 1.00 | 1.00 | match |  |
| OftCropK | 483 | 483 | match |  |
| OftCropPct | 96.6 | 96.6 | match |  |
| OftCropDiff | -2.4 | -2.4 | match |  |
| OftCropLo | -4.2 | -4.2 | match | edge; 20,000 draws give -4.2 or -4.0 |
| OftCropHi | -0.8 | -0.8 | match |  |
| OftCropUB | 3.8 | 3.8 | match |  |
| OftCropLost | 15 | 15 | match |  |
| OftCropGained | 3 | 3 | match |  |
| OftCropFlips | 18 | 18 | match |  |
| OftCropP | 0.008 | 0.008 | match |  |
| OftCropBand | 1.7 | 1.7 | match |  |
| OftCropFlipPct | 3.6 | 3.6 | match |  |
| OftCropHolm | 0.053 | 0.053 | match |  |
| OftBilK | 496 | 496 | match |  |
| OftBilPct | 99.2 | 99.2 | match |  |
| OftBilDiff | +0.2 | +0.2 | match |  |
| OftBilLo | -0.8 | -0.8 | match |  |
| OftBilHi | +1.2 | +1.2 | match |  |
| OftBilUB | 0.6 | 0.6 | match |  |
| OftBilLost | 3 | 3 | match |  |
| OftBilGained | 4 | 4 | match |  |
| OftBilFlips | 7 | 7 | match |  |
| OftBilP | 1.00 | 1.00 | match |  |
| OftBilBand | 1.0 | 1.0 | match |  |
| OftBilFlipPct | 1.4 | 1.4 | match |  |
| OftBilHolm | 1.00 | 1.00 | match |  |
| OftRendK | 491 | 491 | match |  |
| OftRendPct | 98.2 | 98.2 | match |  |
| OftRendDiff | -0.8 | -0.8 | match |  |
| OftRendLo | -2.0 | -2.0 | match | edge; 20,000 draws give -2.2 or -2.0 |
| OftRendHi | +0.4 | +0.4 | match |  |
| OftRendUB | 1.8 | 1.8 | match |  |
| OftRendLost | 7 | 7 | match |  |
| OftRendGained | 3 | 3 | match |  |
| OftRendFlips | 10 | 10 | match |  |
| OftRendP | 0.34 | 0.34 | match |  |
| OftRendBand | 1.2 | 1.2 | match |  |
| OftRendFlipPct | 2.0 | 2.0 | match |  |
| OftRendHolm | 1.00 | 1.00 | match |  |
| OftFlipsMin | 7 | 7 | match |  |
| OftFlipsMax | 18 | 18 | match |  |
| OftBandMin | 1.0 | 1.0 | match |  |
| OftBandMax | 1.7 | 1.7 | match |  |
| OftVarMinPct | 96.6 | 96.6 | match |  |
| OftVarMaxPct | 99.2 | 99.2 | match |  |
| CpuCtrlP | 0.008 | 0.008 | match |  |
| SevRerunSame | 497 | 497 | match |  |
| RerunBoth | 423 | 423 | match |  |
| RerunSameStep | 415 | 415 | match |  |
| OftRerunSame | 500 | 500 | match |  |
| CpuCtrlK | 483 | 483 | match |  |
| CpuCtrlSame | 500 | 500 | match |  |
| CpuCtrlDiffer | 0 | 0 | match |  |
| CpuCtrlLost | 15 | 15 | match |  |
| CpuCtrlGained | 3 | 3 | match |  |
| SevAlways | 296 | 296 | match |  |
| SevNever | 15 | 15 | match |  |
| SevChange | 189 | 189 | match |  |
| SevRefFail | 75 | 75 | match |  |
| SevRescued | 60 | 60 | match |  |
| OftAlways | 470 | 470 | match |  |
| OftNever | 1 | 1 | match |  |
| OftChange | 29 | 29 | match |  |
| OftChangeTaskFive | 13 | 13 | match |  |
| SevOverlapMin | 33 | 33 | match |  |
| SevOverlapMax | 40 | 40 | match |  |
| SevChanceMin | 12.0 | 12 | match |  |
| SevChanceMax | 15.3 | 15.3 | match |  |
| SevOverlapRatioMin | 2.5 | 2.5 | match |  |
| SevOverlapRatioMax | 2.9 | 2.9 | match |  |
| SevVVfMin | 85 | 85 | match |  |
| SevVVfMax | 99 | 99 | match |  |
| SevVVpMin | 0.23 | 0.23 | match |  |
| SevSplitRefA | 161 | 161 | match |  |
| SevSplitRefB | 264 | 264 | match |  |
| SevSplitVarAMin | 163 | 163 | match |  |
| SevSplitVarAMax | 168 | 168 | match |  |
| SevSplitVarBMin | 251 | 251 | match |  |
| SevSplitVarBMax | 260 | 260 | match |  |
| SevSameStepMin | 3 | 3 | match |  |
| SevSameStepMax | 5 | 5 | match |  |
| SevStepDiffMin | 5 | 5 | match |  |
| SevStepDiffMax | 8 | 8 | match |  |
| OftSameStepMin | 9 | 9 | match |  |
| OftSameStepMax | 35 | 35 | match |  |
| OftStepDiffMin | 1 | 1 | match |  |
| OftStepDiffMax | 3 | 3 | match |  |
| OftCropNoFiveLost | 6 | 6 | match |  |
| OftCropNoFiveGained | 2 | 2 | match |  |
| OftCropNoFiveP | 0.29 | 0.29 | match |  |
| OftCropTaskFiveLost | 9 | 9 | match |  |
| OftTaskFiveCrop | 40 | 40 | match |  |
| OftTaskFiveOthersMin | 45 | 45 | match |  |
| OftTaskFiveOthersMax | 48 | 48 | match |  |
| OftCropVsBilLost | 15 | 15 | match |  |
| OftCropVsBilGained | 2 | 2 | match |  |
| AblUnpairedLo | -5.2 | -5.2 | match |  |
| AblUnpairedHi | +3.6 | +3.6 | match |  |
| AblUnpairedUB | 4.6 | 4.6 | match |  |
| AblPairedLo | -4.2 | -4.2 | match |  |
| AblPairedHi | +2.6 | +2.6 | match |  |
| AblPairedUB | 3.6 | 3.6 | match |  |
| AblFirstLost | 14 | 14 | match |  |
| AblFirstGained | 21 | 21 | match |  |
| AblFirstDiff | +3.5 | +3.5 | match |  |
| AblFirstLo | -2.5 | -2.5 | match |  |
| AblFirstHi | +9.5 | +9.5 | match |  |
| AblFirstUB | 1.5 | 1.5 | match |  |
| AblLooMin | -1.6 | -1.6 | match |  |
| AblLooMax | -0.2 | -0.2 | match |  |
| PilotLost | 14 | 14 | match |  |
| PilotGained | 21 | 21 | match |  |
| PilotFlips | 35 | 35 | match |  |
| PilotDisc | 17.5 | 17.5 | match |  |
| PilotDiff | +3.5 | +3.5 | match |  |
| PilotF | 87.5 | 87.5 | match |  |
| PilotSD | 9.4 | 9.4 | match |  |
| PilotBandEp | 18.3 | 18.3 | match |  |
| PilotBandPts | 3.7 | 3.7 | match |  |
| FinalSD | 8.6 | 8.6 | match |  |
| FinalBandEp | 16.9 | 16.9 | match |  |
| PilotMaxDiffVsFinal | 1 | 1 | match |  |
| OlSevFirstN | 500 | 500 | match |  |
| OlSevFirstEpisodes | 500 | 500 | match |  |
| OlSevFirstAgainChanged | 0 | 0 | match |  |
| OlSevFirstAgainMean | 0.0 | 0 | match |  |
| OlSevFirstJpegChanged | 29 | 29 | match |  |
| OlSevFirstJpegMean | 3.3 | 3.3 | match |  |
| OlSevFirstCropChanged | 95 | 95 | match |  |
| OlSevFirstCropMean | 14.4 | 14.4 | match |  |
| OlSevFirstBilChanged | 54 | 54 | match |  |
| OlSevFirstBilMean | 6.9 | 6.9 | match |  |
| OlSevFirstRendChanged | 78 | 78 | match |  |
| OlSevFirstRendMean | 11.8 | 11.8 | match |  |
| OlSevTrajN | 1713 | 1713 | match |  |
| OlSevTrajEpisodes | 50 | 50 | match |  |
| OlSevTrajAgainChanged | 0 | 0 | match |  |
| OlSevTrajAgainMean | 0.0 | 0 | match |  |
| OlSevTrajJpegChanged | 35 | 35 | match |  |
| OlSevTrajJpegMean | 4.1 | 4.1 | match |  |
| OlSevTrajCropChanged | 91 | 91 | match |  |
| OlSevTrajCropMean | 14.0 | 14 | match |  |
| OlSevTrajBilChanged | 55 | 55 | match |  |
| OlSevTrajBilMean | 7.0 | 7 | match |  |
| OlSevTrajRendChanged | 66 | 66 | match |  |
| OlSevTrajRendMean | 8.6 | 8.6 | match |  |
| OlSevTrajRepro | 50 | 50 | match |  |
| OlSevTrajReproN | 50 | 50 | match |  |
| OlOftFirstN | 500 | 500 | match |  |
| OlOftFirstEpisodes | 500 | 500 | match |  |
| OlOftFirstAgainChanged | 0 | 0 | match |  |
| OlOftFirstAgainMean | 0.0 | 0 | match |  |
| OlOftFirstJpegChanged | 99 | 99 | match |  |
| OlOftFirstJpegMean | 0.9 | 0.9 | match |  |
| OlOftFirstCropChanged | 100 | 100 | match |  |
| OlOftFirstCropMean | 10.1 | 10.1 | match |  |
| OlOftFirstBilChanged | 100 | 100 | match |  |
| OlOftFirstBilMean | 2.4 | 2.4 | match |  |
| OlOftFirstRendChanged | 100 | 100 | match |  |
| OlOftFirstRendMean | 1.3 | 1.3 | match |  |
| OlOftTrajN | 1326 | 1326 | match |  |
| OlOftTrajEpisodes | 100 | 100 | match |  |
| OlOftTrajAgainChanged | 0 | 0 | match |  |
| OlOftTrajAgainMean | 0.0 | 0 | match |  |
| OlOftTrajJpegChanged | 84 | 84 | match |  |
| OlOftTrajJpegMean | 0.5 | 0.5 | match |  |
| OlOftTrajCropChanged | 100 | 100 | match |  |
| OlOftTrajCropMean | 5.6 | 5.6 | match |  |
| OlOftTrajBilChanged | 97 | 97 | match |  |
| OlOftTrajBilMean | 0.9 | 0.9 | match |  |
| OlOftTrajRendChanged | 97 | 97 | match |  |
| OlOftTrajRendMean | 0.8 | 0.8 | match |  |
| OlOftTrajRepro | 99 | 99 | match |  |
| OlOftTrajReproN | 100 | 100 | match |  |
| OftCropVsBilP | 0.002 | 0.002 | match |  |
| AblPairedW | 6.8 | 6.8 | match |  |
| AblUnpairedW | 8.8 | 8.8 | match |  |
| AblFirstW | 12.0 | 12.0 | match |  |
| PilotCells | seven | seven | match |  |

281 of 281 macros match; 0 differ or are absent.
