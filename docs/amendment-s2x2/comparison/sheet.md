# S2 / X2 / SX2 comparison

Local counts only. A negative signed delta means the first arm has fewer local tokens than the second. These figures are not billed savings, accuracy, or the closed 1/10 target. No hard cap is proposed.

The request count serializes `{model: UNSELECTED, temperature: 0.001, store: false, tools}` and omits messages because this packet does not load questions. `cl100k_base` is not used to choose an edit.

Gold-linked rival check: not run. It would be a scoring diagnostic after this freeze, and gold is not an editing input.

## Fixtures

```json
{
  "passed": true,
  "multiple_34": {
    "math_gcd": "Unlike math_lcm, which calculates the least common multiple, this calculates the greatest common divisor.",
    "math_lcm": "Unlike math_gcd, which calculates the greatest common divisor, this calculates the least common multiple.",
    "math_sqrt_cue": ""
  },
  "multiple_35": {
    "calculate_lcm": "Unlike calculate_gcd, which calculates the greatest common divisor (gcd), this calculates the least common multiple (lcm).",
    "calculate_gcd": "Unlike calculate_lcm, which calculates the least common multiple (lcm), this calculates the greatest common divisor (gcd)."
  },
  "multiple_11": {
    "math_roots_quadratic": "Unlike math_roots_polynomial, which takes an ordered coefficient array, this takes named quadratic coefficients.",
    "math_roots_cubic": "Unlike math_roots_polynomial, which takes an ordered coefficient array, this takes named cubic coefficients.",
    "math_roots_polynomial": "Unlike math_roots_quadratic, which takes named quadratic coefficients, this takes an ordered coefficient array."
  },
  "get_angles": "Whether to calculate the internal angles",
  "controls_checked": 640,
  "control_examples": [
    "simple_python_0",
    "irrelevance_0"
  ],
  "control_comparison": "tool list and request envelope bytes; wrapper condition labels may differ",
  "gold_linked_rival_check": {
    "ran": false,
    "reason": "Scoring-only diagnostic. Gold is not loaded."
  }
}
```

## Exposed formative cases

These 12 cases were opened by the earlier pilot. They are identified whether or not this amendment changes them.

- `multiple_35` (multiple): amendment no-op `False`; arms equal to U: U, pr12_S
- `multiple_0` (multiple): amendment no-op `False`; arms equal to U: U, X2
- `multiple_11` (multiple): amendment no-op `False`; arms equal to U: U, pr12_S, pr12_X, pr12_SX
- `multiple_12` (multiple): amendment no-op `False`; arms equal to U: U, pr12_S, X2
- `multiple_7` (multiple): amendment no-op `True`; arms equal to U: U, pr12_S, pr12_X, pr12_SX, S2, X2, SX2
- `multiple_92` (multiple): amendment no-op `False`; arms equal to U: U, systems_test_S, pr12_S, S2
- `multiple_153` (multiple): amendment no-op `False`; arms equal to U: U, systems_test_X, pr12_S, pr12_X, pr12_SX, X2
- `multiple_100` (multiple): amendment no-op `False`; arms equal to U: U, systems_test_X, pr12_X, X2
- `simple_python_175` (simple_python): amendment no-op `True`; arms equal to U: U, systems_test_X, pr12_S, pr12_X, pr12_SX, S2, X2, SX2
- `simple_python_34` (simple_python): amendment no-op `True`; arms equal to U: U, systems_test_X, pr12_S, pr12_X, pr12_SX, S2, X2, SX2
- `irrelevance_59` (irrelevance): amendment no-op `True`; arms equal to U: U, systems_test_S, systems_test_X, systems_test_SX, pr12_S, pr12_X, pr12_SX, S2, X2, SX2
- `irrelevance_50` (irrelevance): amendment no-op `False`; arms equal to U: U, systems_test_S, systems_test_X, systems_test_SX, pr12_S, pr12_X, pr12_SX, X2

## No-op cases

A no-op case has no adopted S2 field and no X2 cue. The full id list is below, not only the changed cases.

### multiple (105)

`multiple_3`, `multiple_5`, `multiple_7`, `multiple_13`, `multiple_15`, `multiple_18`, `multiple_22`, `multiple_23`, `multiple_25`, `multiple_26`, `multiple_27`, `multiple_28`, `multiple_29`, `multiple_31`, `multiple_33`, `multiple_38`, `multiple_42`, `multiple_45`, `multiple_46`, `multiple_47`, `multiple_50`, `multiple_54`, `multiple_56`, `multiple_58`, `multiple_59`, `multiple_61`, `multiple_62`, `multiple_65`, `multiple_66`, `multiple_67`, `multiple_69`, `multiple_70`, `multiple_71`, `multiple_73`, `multiple_74`, `multiple_75`, `multiple_76`, `multiple_77`, `multiple_78`, `multiple_79`, `multiple_80`, `multiple_81`, `multiple_83`, `multiple_84`, `multiple_86`, `multiple_87`, `multiple_88`, `multiple_89`, `multiple_90`, `multiple_91`, `multiple_93`, `multiple_94`, `multiple_95`, `multiple_98`, `multiple_99`, `multiple_101`, `multiple_104`, `multiple_107`, `multiple_109`, `multiple_112`, `multiple_113`, `multiple_114`, `multiple_116`, `multiple_118`, `multiple_121`, `multiple_123`, `multiple_125`, `multiple_128`, `multiple_130`, `multiple_131`, `multiple_136`, `multiple_137`, `multiple_140`, `multiple_141`, `multiple_143`, `multiple_144`, `multiple_146`, `multiple_147`, `multiple_148`, `multiple_149`, `multiple_151`, `multiple_152`, `multiple_154`, `multiple_157`, `multiple_160`, `multiple_161`, `multiple_162`, `multiple_163`, `multiple_166`, `multiple_168`, `multiple_169`, `multiple_170`, `multiple_171`, `multiple_177`, `multiple_179`, `multiple_180`, `multiple_183`, `multiple_184`, `multiple_185`, `multiple_186`, `multiple_189`, `multiple_194`, `multiple_195`, `multiple_197`, `multiple_199`

### simple_python (331)

`simple_python_0`, `simple_python_1`, `simple_python_2`, `simple_python_3`, `simple_python_4`, `simple_python_5`, `simple_python_6`, `simple_python_7`, `simple_python_8`, `simple_python_9`, `simple_python_10`, `simple_python_11`, `simple_python_12`, `simple_python_13`, `simple_python_15`, `simple_python_16`, `simple_python_17`, `simple_python_18`, `simple_python_19`, `simple_python_20`, `simple_python_21`, `simple_python_22`, `simple_python_24`, `simple_python_26`, `simple_python_27`, `simple_python_33`, `simple_python_34`, `simple_python_35`, `simple_python_36`, `simple_python_37`, `simple_python_45`, `simple_python_47`, `simple_python_48`, `simple_python_49`, `simple_python_50`, `simple_python_51`, `simple_python_52`, `simple_python_53`, `simple_python_54`, `simple_python_55`, `simple_python_56`, `simple_python_58`, `simple_python_59`, `simple_python_60`, `simple_python_61`, `simple_python_62`, `simple_python_63`, `simple_python_65`, `simple_python_66`, `simple_python_67`, `simple_python_68`, `simple_python_69`, `simple_python_71`, `simple_python_72`, `simple_python_74`, `simple_python_76`, `simple_python_77`, `simple_python_78`, `simple_python_79`, `simple_python_80`, `simple_python_81`, `simple_python_82`, `simple_python_83`, `simple_python_84`, `simple_python_85`, `simple_python_86`, `simple_python_87`, `simple_python_89`, `simple_python_90`, `simple_python_91`, `simple_python_92`, `simple_python_93`, `simple_python_94`, `simple_python_95`, `simple_python_96`, `simple_python_97`, `simple_python_98`, `simple_python_100`, `simple_python_101`, `simple_python_102`, `simple_python_103`, `simple_python_104`, `simple_python_105`, `simple_python_106`, `simple_python_107`, `simple_python_108`, `simple_python_109`, `simple_python_110`, `simple_python_111`, `simple_python_112`, `simple_python_113`, `simple_python_116`, `simple_python_117`, `simple_python_120`, `simple_python_125`, `simple_python_126`, `simple_python_128`, `simple_python_132`, `simple_python_135`, `simple_python_140`, `simple_python_141`, `simple_python_142`, `simple_python_143`, `simple_python_144`, `simple_python_146`, `simple_python_147`, `simple_python_149`, `simple_python_151`, `simple_python_156`, `simple_python_158`, `simple_python_159`, `simple_python_160`, `simple_python_161`, `simple_python_162`, `simple_python_164`, `simple_python_165`, `simple_python_166`, `simple_python_167`, `simple_python_168`, `simple_python_169`, `simple_python_170`, `simple_python_171`, `simple_python_172`, `simple_python_173`, `simple_python_174`, `simple_python_175`, `simple_python_176`, `simple_python_177`, `simple_python_178`, `simple_python_179`, `simple_python_180`, `simple_python_181`, `simple_python_182`, `simple_python_183`, `simple_python_184`, `simple_python_185`, `simple_python_186`, `simple_python_187`, `simple_python_188`, `simple_python_189`, `simple_python_190`, `simple_python_191`, `simple_python_192`, `simple_python_193`, `simple_python_194`, `simple_python_195`, `simple_python_196`, `simple_python_197`, `simple_python_198`, `simple_python_199`, `simple_python_201`, `simple_python_202`, `simple_python_203`, `simple_python_204`, `simple_python_205`, `simple_python_206`, `simple_python_207`, `simple_python_208`, `simple_python_209`, `simple_python_210`, `simple_python_211`, `simple_python_212`, `simple_python_213`, `simple_python_214`, `simple_python_216`, `simple_python_218`, `simple_python_219`, `simple_python_222`, `simple_python_223`, `simple_python_224`, `simple_python_225`, `simple_python_226`, `simple_python_227`, `simple_python_228`, `simple_python_229`, `simple_python_230`, `simple_python_231`, `simple_python_232`, `simple_python_233`, `simple_python_234`, `simple_python_235`, `simple_python_236`, `simple_python_237`, `simple_python_238`, `simple_python_239`, `simple_python_240`, `simple_python_241`, `simple_python_242`, `simple_python_243`, `simple_python_244`, `simple_python_245`, `simple_python_246`, `simple_python_247`, `simple_python_248`, `simple_python_249`, `simple_python_250`, `simple_python_251`, `simple_python_253`, `simple_python_254`, `simple_python_255`, `simple_python_256`, `simple_python_258`, `simple_python_259`, `simple_python_260`, `simple_python_261`, `simple_python_262`, `simple_python_263`, `simple_python_264`, `simple_python_265`, `simple_python_266`, `simple_python_267`, `simple_python_268`, `simple_python_270`, `simple_python_271`, `simple_python_272`, `simple_python_273`, `simple_python_274`, `simple_python_275`, `simple_python_276`, `simple_python_277`, `simple_python_278`, `simple_python_279`, `simple_python_280`, `simple_python_281`, `simple_python_282`, `simple_python_283`, `simple_python_284`, `simple_python_285`, `simple_python_286`, `simple_python_287`, `simple_python_288`, `simple_python_289`, `simple_python_290`, `simple_python_291`, `simple_python_292`, `simple_python_293`, `simple_python_294`, `simple_python_295`, `simple_python_297`, `simple_python_298`, `simple_python_299`, `simple_python_300`, `simple_python_301`, `simple_python_302`, `simple_python_303`, `simple_python_304`, `simple_python_305`, `simple_python_306`, `simple_python_307`, `simple_python_308`, `simple_python_309`, `simple_python_310`, `simple_python_311`, `simple_python_312`, `simple_python_313`, `simple_python_314`, `simple_python_315`, `simple_python_316`, `simple_python_317`, `simple_python_318`, `simple_python_319`, `simple_python_320`, `simple_python_321`, `simple_python_322`, `simple_python_323`, `simple_python_324`, `simple_python_325`, `simple_python_328`, `simple_python_329`, `simple_python_330`, `simple_python_331`, `simple_python_332`, `simple_python_333`, `simple_python_334`, `simple_python_335`, `simple_python_336`, `simple_python_337`, `simple_python_338`, `simple_python_339`, `simple_python_340`, `simple_python_341`, `simple_python_342`, `simple_python_343`, `simple_python_344`, `simple_python_345`, `simple_python_347`, `simple_python_348`, `simple_python_349`, `simple_python_350`, `simple_python_352`, `simple_python_353`, `simple_python_354`, `simple_python_355`, `simple_python_356`, `simple_python_357`, `simple_python_358`, `simple_python_359`, `simple_python_360`, `simple_python_361`, `simple_python_363`, `simple_python_364`, `simple_python_365`, `simple_python_366`, `simple_python_367`, `simple_python_369`, `simple_python_370`, `simple_python_371`, `simple_python_372`, `simple_python_373`, `simple_python_374`, `simple_python_375`, `simple_python_376`, `simple_python_377`, `simple_python_378`, `simple_python_379`, `simple_python_380`, `simple_python_381`, `simple_python_382`, `simple_python_383`, `simple_python_384`, `simple_python_386`, `simple_python_387`, `simple_python_388`, `simple_python_390`, `simple_python_393`, `simple_python_394`, `simple_python_395`, `simple_python_396`, `simple_python_397`, `simple_python_398`, `simple_python_399`

### irrelevance (165)

`irrelevance_1`, `irrelevance_2`, `irrelevance_3`, `irrelevance_8`, `irrelevance_10`, `irrelevance_11`, `irrelevance_12`, `irrelevance_29`, `irrelevance_30`, `irrelevance_31`, `irrelevance_33`, `irrelevance_34`, `irrelevance_35`, `irrelevance_36`, `irrelevance_37`, `irrelevance_38`, `irrelevance_41`, `irrelevance_42`, `irrelevance_45`, `irrelevance_46`, `irrelevance_47`, `irrelevance_48`, `irrelevance_49`, `irrelevance_51`, `irrelevance_52`, `irrelevance_53`, `irrelevance_54`, `irrelevance_56`, `irrelevance_59`, `irrelevance_63`, `irrelevance_66`, `irrelevance_73`, `irrelevance_76`, `irrelevance_79`, `irrelevance_80`, `irrelevance_81`, `irrelevance_85`, `irrelevance_86`, `irrelevance_87`, `irrelevance_89`, `irrelevance_90`, `irrelevance_91`, `irrelevance_92`, `irrelevance_93`, `irrelevance_94`, `irrelevance_95`, `irrelevance_96`, `irrelevance_97`, `irrelevance_99`, `irrelevance_100`, `irrelevance_101`, `irrelevance_102`, `irrelevance_103`, `irrelevance_105`, `irrelevance_106`, `irrelevance_107`, `irrelevance_109`, `irrelevance_111`, `irrelevance_112`, `irrelevance_114`, `irrelevance_116`, `irrelevance_118`, `irrelevance_119`, `irrelevance_121`, `irrelevance_122`, `irrelevance_124`, `irrelevance_125`, `irrelevance_126`, `irrelevance_127`, `irrelevance_128`, `irrelevance_129`, `irrelevance_130`, `irrelevance_131`, `irrelevance_132`, `irrelevance_133`, `irrelevance_134`, `irrelevance_135`, `irrelevance_136`, `irrelevance_137`, `irrelevance_138`, `irrelevance_139`, `irrelevance_141`, `irrelevance_142`, `irrelevance_143`, `irrelevance_144`, `irrelevance_145`, `irrelevance_146`, `irrelevance_147`, `irrelevance_148`, `irrelevance_149`, `irrelevance_150`, `irrelevance_151`, `irrelevance_152`, `irrelevance_153`, `irrelevance_154`, `irrelevance_155`, `irrelevance_156`, `irrelevance_157`, `irrelevance_159`, `irrelevance_160`, `irrelevance_161`, `irrelevance_162`, `irrelevance_165`, `irrelevance_166`, `irrelevance_167`, `irrelevance_168`, `irrelevance_169`, `irrelevance_170`, `irrelevance_171`, `irrelevance_172`, `irrelevance_173`, `irrelevance_174`, `irrelevance_175`, `irrelevance_176`, `irrelevance_177`, `irrelevance_178`, `irrelevance_179`, `irrelevance_180`, `irrelevance_181`, `irrelevance_182`, `irrelevance_183`, `irrelevance_184`, `irrelevance_185`, `irrelevance_186`, `irrelevance_187`, `irrelevance_188`, `irrelevance_189`, `irrelevance_190`, `irrelevance_191`, `irrelevance_192`, `irrelevance_193`, `irrelevance_194`, `irrelevance_195`, `irrelevance_196`, `irrelevance_197`, `irrelevance_198`, `irrelevance_199`, `irrelevance_200`, `irrelevance_201`, `irrelevance_202`, `irrelevance_203`, `irrelevance_205`, `irrelevance_206`, `irrelevance_207`, `irrelevance_209`, `irrelevance_210`, `irrelevance_212`, `irrelevance_213`, `irrelevance_218`, `irrelevance_219`, `irrelevance_220`, `irrelevance_222`, `irrelevance_223`, `irrelevance_224`, `irrelevance_225`, `irrelevance_226`, `irrelevance_227`, `irrelevance_228`, `irrelevance_229`, `irrelevance_231`, `irrelevance_232`, `irrelevance_233`, `irrelevance_236`, `irrelevance_237`, `irrelevance_239`

## Counts

## all_840

Fields

| measure | count |
| --- | --- |
| eligible | 4604/4604 |
| proposed | 897/4604 |
| adopted | 429/4604 |
| meaningfully_changed | 429/4604 |
| cosmetic_only | 0/4604 |
| unchanged | 4175/4604 |

Tools

| measure | count |
| --- | --- |
| eligible | 1197/1197 |
| proposed | 650/1197 |
| adopted | 274/1197 |
| meaningfully_changed | 274/1197 |
| cosmetic_only | 0/1197 |
| unchanged | 923/1197 |

Cases

| measure | count |
| --- | --- |
| eligible | 840/840 |
| proposed | 506/840 |
| adopted | 230/840 |
| meaningfully_changed | 230/840 |
| cosmetic_only | 0/840 |
| unchanged | 601/840 |

Cues

| measure | count |
| --- | --- |
| cued_tools | 30/1197 |
| cued_cases | 13/840 |
| controls | 640/840 |
| controls_with_any_cue | 0/640 |
| multi_tool_cases_with_a_cue | 13/200 |
| uncued_tools_in_a_cued_case | 4/34 |

### Field tokens, o200k_base

| arm | tokens |
| --- | ---: |
| U | 55267 |
| S2 | 52327 |
| X2 | 55908 |
| SX2 | 52968 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -2940 |
| X2-U | 641 |
| SX2-S2 | 641 |
| SX2-X2 | -2940 |
| SX2-U | -2299 |

### Whole request tokens without messages, o200k_base

| arm | tokens |
| --- | ---: |
| U | 153316 |
| S2 | 150424 |
| X2 | 153954 |
| SX2 | 151062 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -2892 |
| X2-U | 638 |
| SX2-S2 | 638 |
| SX2-X2 | -2892 |
| SX2-U | -2254 |

Local serialization of model, temperature, store, and tools. Question messages are not loaded. Not provider usage.

### Field tokens, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 55609 |
| S2 | 52671 |
| X2 | 56239 |
| SX2 | 53301 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -2938 |
| X2-U | 630 |
| SX2-S2 | 630 |
| SX2-X2 | -2938 |
| SX2-U | -2308 |

### Whole request tokens without messages, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 151109 |
| S2 | 148212 |
| X2 | 151736 |
| SX2 | 148839 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -2897 |
| X2-U | 627 |
| SX2-S2 | 627 |
| SX2-X2 | -2897 |
| SX2-U | -2270 |

Cue cost across all description fields in the case. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 827/840 |
| cue_consumes_part_of_savings | 0/840 |
| cue_consumes_all_savings | 0/840 |
| cue_exceeds_savings | 4/840 |
| cue_cost_without_s2_savings | 9/840 |

Cue cost on the request envelope. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 827/840 |
| cue_consumes_part_of_savings | 0/840 |
| cue_consumes_all_savings | 0/840 |
| cue_exceeds_savings | 4/840 |
| cue_cost_without_s2_savings | 9/840 |

Cue cost on the one cued function field. Denominator is cued fields in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 0/30 |
| cue_consumes_part_of_savings | 0/30 |
| cue_consumes_all_savings | 0/30 |
| cue_exceeds_savings | 0/30 |
| cue_cost_without_s2_savings | 30/30 |

## multiple

Fields

| measure | count |
| --- | --- |
| eligible | 2101/2101 |
| proposed | 434/2101 |
| adopted | 213/2101 |
| meaningfully_changed | 213/2101 |
| cosmetic_only | 0/2101 |
| unchanged | 1888/2101 |

Tools

| measure | count |
| --- | --- |
| eligible | 557/557 |
| proposed | 310/557 |
| adopted | 130/557 |
| meaningfully_changed | 130/557 |
| cosmetic_only | 0/557 |
| unchanged | 427/557 |

Cases

| measure | count |
| --- | --- |
| eligible | 200/200 |
| proposed | 166/200 |
| adopted | 86/200 |
| meaningfully_changed | 86/200 |
| cosmetic_only | 0/200 |
| unchanged | 105/200 |

Cues

| measure | count |
| --- | --- |
| cued_tools | 30/557 |
| cued_cases | 13/200 |
| controls | 0/200 |
| controls_with_any_cue | 0/0 |
| multi_tool_cases_with_a_cue | 13/200 |
| uncued_tools_in_a_cued_case | 4/34 |

### Field tokens, o200k_base

| arm | tokens |
| --- | ---: |
| U | 24924 |
| S2 | 23462 |
| X2 | 25565 |
| SX2 | 24103 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -1462 |
| X2-U | 641 |
| SX2-S2 | 641 |
| SX2-X2 | -1462 |
| SX2-U | -821 |

### Whole request tokens without messages, o200k_base

| arm | tokens |
| --- | ---: |
| U | 65967 |
| S2 | 64527 |
| X2 | 66605 |
| SX2 | 65165 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -1440 |
| X2-U | 638 |
| SX2-S2 | 638 |
| SX2-X2 | -1440 |
| SX2-U | -802 |

Local serialization of model, temperature, store, and tools. Question messages are not loaded. Not provider usage.

### Field tokens, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 25073 |
| S2 | 23611 |
| X2 | 25703 |
| SX2 | 24241 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -1462 |
| X2-U | 630 |
| SX2-S2 | 630 |
| SX2-X2 | -1462 |
| SX2-U | -832 |

### Whole request tokens without messages, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 65306 |
| S2 | 63864 |
| X2 | 65933 |
| SX2 | 64491 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -1442 |
| X2-U | 627 |
| SX2-S2 | 627 |
| SX2-X2 | -1442 |
| SX2-U | -815 |

Cue cost across all description fields in the case. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 187/200 |
| cue_consumes_part_of_savings | 0/200 |
| cue_consumes_all_savings | 0/200 |
| cue_exceeds_savings | 4/200 |
| cue_cost_without_s2_savings | 9/200 |

Cue cost on the request envelope. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 187/200 |
| cue_consumes_part_of_savings | 0/200 |
| cue_consumes_all_savings | 0/200 |
| cue_exceeds_savings | 4/200 |
| cue_cost_without_s2_savings | 9/200 |

Cue cost on the one cued function field. Denominator is cued fields in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 0/30 |
| cue_consumes_part_of_savings | 0/30 |
| cue_consumes_all_savings | 0/30 |
| cue_exceeds_savings | 0/30 |
| cue_cost_without_s2_savings | 30/30 |

## simple_python

Fields

| measure | count |
| --- | --- |
| eligible | 1570/1570 |
| proposed | 268/1570 |
| adopted | 77/1570 |
| meaningfully_changed | 77/1570 |
| cosmetic_only | 0/1570 |
| unchanged | 1493/1570 |

Tools

| measure | count |
| --- | --- |
| eligible | 400/400 |
| proposed | 222/400 |
| adopted | 69/400 |
| meaningfully_changed | 69/400 |
| cosmetic_only | 0/400 |
| unchanged | 331/400 |

Cases

| measure | count |
| --- | --- |
| eligible | 400/400 |
| proposed | 222/400 |
| adopted | 69/400 |
| meaningfully_changed | 69/400 |
| cosmetic_only | 0/400 |
| unchanged | 331/400 |

Cues

| measure | count |
| --- | --- |
| cued_tools | 0/400 |
| cued_cases | 0/400 |
| controls | 400/400 |
| controls_with_any_cue | 0/400 |
| multi_tool_cases_with_a_cue | 0/0 |
| uncued_tools_in_a_cued_case | 0/0 |

### Field tokens, o200k_base

| arm | tokens |
| --- | ---: |
| U | 18894 |
| S2 | 18386 |
| X2 | 18894 |
| SX2 | 18386 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -508 |
| X2-U | 0 |
| SX2-S2 | 0 |
| SX2-X2 | -508 |
| SX2-U | -508 |

### Whole request tokens without messages, o200k_base

| arm | tokens |
| --- | ---: |
| U | 54239 |
| S2 | 53743 |
| X2 | 54239 |
| SX2 | 53743 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -496 |
| X2-U | 0 |
| SX2-S2 | 0 |
| SX2-X2 | -496 |
| SX2-U | -496 |

Local serialization of model, temperature, store, and tools. Question messages are not loaded. Not provider usage.

### Field tokens, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 19012 |
| S2 | 18505 |
| X2 | 19012 |
| SX2 | 18505 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -507 |
| X2-U | 0 |
| SX2-S2 | 0 |
| SX2-X2 | -507 |
| SX2-U | -507 |

### Whole request tokens without messages, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 53320 |
| S2 | 52824 |
| X2 | 53320 |
| SX2 | 52824 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -496 |
| X2-U | 0 |
| SX2-S2 | 0 |
| SX2-X2 | -496 |
| SX2-U | -496 |

Cue cost across all description fields in the case. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 400/400 |
| cue_consumes_part_of_savings | 0/400 |
| cue_consumes_all_savings | 0/400 |
| cue_exceeds_savings | 0/400 |
| cue_cost_without_s2_savings | 0/400 |

Cue cost on the request envelope. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 400/400 |
| cue_consumes_part_of_savings | 0/400 |
| cue_consumes_all_savings | 0/400 |
| cue_exceeds_savings | 0/400 |
| cue_cost_without_s2_savings | 0/400 |

Cue cost on the one cued function field. Denominator is cued fields in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 0/0 |
| cue_consumes_part_of_savings | 0/0 |
| cue_consumes_all_savings | 0/0 |
| cue_exceeds_savings | 0/0 |
| cue_cost_without_s2_savings | 0/0 |

## irrelevance

Fields

| measure | count |
| --- | --- |
| eligible | 933/933 |
| proposed | 195/933 |
| adopted | 139/933 |
| meaningfully_changed | 139/933 |
| cosmetic_only | 0/933 |
| unchanged | 794/933 |

Tools

| measure | count |
| --- | --- |
| eligible | 240/240 |
| proposed | 118/240 |
| adopted | 75/240 |
| meaningfully_changed | 75/240 |
| cosmetic_only | 0/240 |
| unchanged | 165/240 |

Cases

| measure | count |
| --- | --- |
| eligible | 240/240 |
| proposed | 118/240 |
| adopted | 75/240 |
| meaningfully_changed | 75/240 |
| cosmetic_only | 0/240 |
| unchanged | 165/240 |

Cues

| measure | count |
| --- | --- |
| cued_tools | 0/240 |
| cued_cases | 0/240 |
| controls | 240/240 |
| controls_with_any_cue | 0/240 |
| multi_tool_cases_with_a_cue | 0/0 |
| uncued_tools_in_a_cued_case | 0/0 |

### Field tokens, o200k_base

| arm | tokens |
| --- | ---: |
| U | 11449 |
| S2 | 10479 |
| X2 | 11449 |
| SX2 | 10479 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -970 |
| X2-U | 0 |
| SX2-S2 | 0 |
| SX2-X2 | -970 |
| SX2-U | -970 |

### Whole request tokens without messages, o200k_base

| arm | tokens |
| --- | ---: |
| U | 33110 |
| S2 | 32154 |
| X2 | 33110 |
| SX2 | 32154 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -956 |
| X2-U | 0 |
| SX2-S2 | 0 |
| SX2-X2 | -956 |
| SX2-U | -956 |

Local serialization of model, temperature, store, and tools. Question messages are not loaded. Not provider usage.

### Field tokens, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 11524 |
| S2 | 10555 |
| X2 | 11524 |
| SX2 | 10555 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -969 |
| X2-U | 0 |
| SX2-S2 | 0 |
| SX2-X2 | -969 |
| SX2-U | -969 |

### Whole request tokens without messages, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 32483 |
| S2 | 31524 |
| X2 | 32483 |
| SX2 | 31524 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -959 |
| X2-U | 0 |
| SX2-S2 | 0 |
| SX2-X2 | -959 |
| SX2-U | -959 |

Cue cost across all description fields in the case. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 240/240 |
| cue_consumes_part_of_savings | 0/240 |
| cue_consumes_all_savings | 0/240 |
| cue_exceeds_savings | 0/240 |
| cue_cost_without_s2_savings | 0/240 |

Cue cost on the request envelope. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 240/240 |
| cue_consumes_part_of_savings | 0/240 |
| cue_consumes_all_savings | 0/240 |
| cue_exceeds_savings | 0/240 |
| cue_cost_without_s2_savings | 0/240 |

Cue cost on the one cued function field. Denominator is cued fields in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 0/0 |
| cue_consumes_part_of_savings | 0/0 |
| cue_consumes_all_savings | 0/0 |
| cue_exceeds_savings | 0/0 |
| cue_cost_without_s2_savings | 0/0 |

## formative_12

Fields

| measure | count |
| --- | --- |
| eligible | 95/95 |
| proposed | 29/95 |
| adopted | 22/95 |
| meaningfully_changed | 22/95 |
| cosmetic_only | 0/95 |
| unchanged | 73/95 |

Tools

| measure | count |
| --- | --- |
| eligible | 24/24 |
| proposed | 17/24 |
| adopted | 11/24 |
| meaningfully_changed | 11/24 |
| cosmetic_only | 0/24 |
| unchanged | 13/24 |

Cases

| measure | count |
| --- | --- |
| eligible | 12/12 |
| proposed | 8/12 |
| adopted | 7/12 |
| meaningfully_changed | 7/12 |
| cosmetic_only | 0/12 |
| unchanged | 4/12 |

Cues

| measure | count |
| --- | --- |
| cued_tools | 8/24 |
| cued_cases | 3/12 |
| controls | 4/12 |
| controls_with_any_cue | 0/4 |
| multi_tool_cases_with_a_cue | 3/8 |
| uncued_tools_in_a_cued_case | 0/8 |

### Field tokens, o200k_base

| arm | tokens |
| --- | ---: |
| U | 1051 |
| S2 | 874 |
| X2 | 1251 |
| SX2 | 1074 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -177 |
| X2-U | 200 |
| SX2-S2 | 200 |
| SX2-X2 | -177 |
| SX2-U | 23 |

### Whole request tokens without messages, o200k_base

| arm | tokens |
| --- | ---: |
| U | 3012 |
| S2 | 2839 |
| X2 | 3211 |
| SX2 | 3038 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -173 |
| X2-U | 199 |
| SX2-S2 | 199 |
| SX2-X2 | -173 |
| SX2-U | 26 |

Local serialization of model, temperature, store, and tools. Question messages are not loaded. Not provider usage.

### Field tokens, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 1051 |
| S2 | 873 |
| X2 | 1245 |
| SX2 | 1067 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -178 |
| X2-U | 194 |
| SX2-S2 | 194 |
| SX2-X2 | -178 |
| SX2-U | 16 |

### Whole request tokens without messages, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 2970 |
| S2 | 2796 |
| X2 | 3163 |
| SX2 | 2989 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -174 |
| X2-U | 193 |
| SX2-S2 | 193 |
| SX2-X2 | -174 |
| SX2-U | 19 |

Cue cost across all description fields in the case. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 9/12 |
| cue_consumes_part_of_savings | 0/12 |
| cue_consumes_all_savings | 0/12 |
| cue_exceeds_savings | 2/12 |
| cue_cost_without_s2_savings | 1/12 |

Cue cost on the request envelope. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 9/12 |
| cue_consumes_part_of_savings | 0/12 |
| cue_consumes_all_savings | 0/12 |
| cue_exceeds_savings | 2/12 |
| cue_cost_without_s2_savings | 1/12 |

Cue cost on the one cued function field. Denominator is cued fields in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 0/8 |
| cue_consumes_part_of_savings | 0/8 |
| cue_consumes_all_savings | 0/8 |
| cue_exceeds_savings | 0/8 |
| cue_cost_without_s2_savings | 8/8 |

## excluding_formative_12

Fields

| measure | count |
| --- | --- |
| eligible | 4509/4509 |
| proposed | 868/4509 |
| adopted | 407/4509 |
| meaningfully_changed | 407/4509 |
| cosmetic_only | 0/4509 |
| unchanged | 4102/4509 |

Tools

| measure | count |
| --- | --- |
| eligible | 1173/1173 |
| proposed | 633/1173 |
| adopted | 263/1173 |
| meaningfully_changed | 263/1173 |
| cosmetic_only | 0/1173 |
| unchanged | 910/1173 |

Cases

| measure | count |
| --- | --- |
| eligible | 828/828 |
| proposed | 498/828 |
| adopted | 223/828 |
| meaningfully_changed | 223/828 |
| cosmetic_only | 0/828 |
| unchanged | 597/828 |

Cues

| measure | count |
| --- | --- |
| cued_tools | 22/1173 |
| cued_cases | 10/828 |
| controls | 636/828 |
| controls_with_any_cue | 0/636 |
| multi_tool_cases_with_a_cue | 10/192 |
| uncued_tools_in_a_cued_case | 4/26 |

### Field tokens, o200k_base

| arm | tokens |
| --- | ---: |
| U | 54216 |
| S2 | 51453 |
| X2 | 54657 |
| SX2 | 51894 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -2763 |
| X2-U | 441 |
| SX2-S2 | 441 |
| SX2-X2 | -2763 |
| SX2-U | -2322 |

### Whole request tokens without messages, o200k_base

| arm | tokens |
| --- | ---: |
| U | 150304 |
| S2 | 147585 |
| X2 | 150743 |
| SX2 | 148024 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -2719 |
| X2-U | 439 |
| SX2-S2 | 439 |
| SX2-X2 | -2719 |
| SX2-U | -2280 |

Local serialization of model, temperature, store, and tools. Question messages are not loaded. Not provider usage.

### Field tokens, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 54558 |
| S2 | 51798 |
| X2 | 54994 |
| SX2 | 52234 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -2760 |
| X2-U | 436 |
| SX2-S2 | 436 |
| SX2-X2 | -2760 |
| SX2-U | -2324 |

### Whole request tokens without messages, cl100k_base, not used for selection

| arm | tokens |
| --- | ---: |
| U | 148139 |
| S2 | 145416 |
| X2 | 148573 |
| SX2 | 145850 |

| signed delta | tokens |
| --- | ---: |
| S2-U | -2723 |
| X2-U | 434 |
| SX2-S2 | 434 |
| SX2-X2 | -2723 |
| SX2-U | -2289 |

Cue cost across all description fields in the case. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 818/828 |
| cue_consumes_part_of_savings | 0/828 |
| cue_consumes_all_savings | 0/828 |
| cue_exceeds_savings | 2/828 |
| cue_cost_without_s2_savings | 8/828 |

Cue cost on the request envelope. Denominator is every case in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 818/828 |
| cue_consumes_part_of_savings | 0/828 |
| cue_consumes_all_savings | 0/828 |
| cue_exceeds_savings | 2/828 |
| cue_cost_without_s2_savings | 8/828 |

Cue cost on the one cued function field. Denominator is cued fields in this scope.

| measure | count |
| --- | --- |
| cue_adds_no_tokens | 0/22 |
| cue_consumes_part_of_savings | 0/22 |
| cue_consumes_all_savings | 0/22 |
| cue_exceeds_savings | 0/22 |
| cue_cost_without_s2_savings | 22/22 |

## Where the cue spends the saving

Cases whose cue exceeds the S2 field-token saving:

`multiple_11`, `multiple_34`, `multiple_35`, `multiple_72`

Cases whose cue exceeds the S2 request-token saving:

`multiple_11`, `multiple_34`, `multiple_35`, `multiple_72`

Cued function fields whose own cue exceeds that field's S2 saving:

`multiple_2` country_info_largest_city (cue_cost_without_s2_savings, SX2-U 20); `multiple_2` country_info_capital (cue_cost_without_s2_savings, SX2-U 21); `multiple_11` math_roots_quadratic (cue_cost_without_s2_savings, SX2-U 20); `multiple_11` math_roots_cubic (cue_cost_without_s2_savings, SX2-U 20); `multiple_11` math_roots_polynomial (cue_cost_without_s2_savings, SX2-U 21); `multiple_19` religion_history_get_councils (cue_cost_without_s2_savings, SX2-U 24); `multiple_19` religion_history_get_reformations (cue_cost_without_s2_savings, SX2-U 26); `multiple_19` religion_history_get_schisms (cue_cost_without_s2_savings, SX2-U 26); `multiple_34` math_gcd (cue_cost_without_s2_savings, SX2-U 19); `multiple_34` math_lcm (cue_cost_without_s2_savings, SX2-U 19); `multiple_35` calculate_lcm (cue_cost_without_s2_savings, SX2-U 25); `multiple_35` calculate_gcd (cue_cost_without_s2_savings, SX2-U 25); `multiple_48` store_find_nearby (cue_cost_without_s2_savings, SX2-U 19); `multiple_48` library_find_nearby (cue_cost_without_s2_savings, SX2-U 19); `multiple_53` linear_regression (cue_cost_without_s2_savings, SX2-U 18); `multiple_53` random_forest_regression (cue_cost_without_s2_savings, SX2-U 16); `multiple_63` air_quality_forecast (cue_cost_without_s2_savings, SX2-U 18); `multiple_63` weather_forecast (cue_cost_without_s2_savings, SX2-U 19); `multiple_64` uv_index_get_future (cue_cost_without_s2_savings, SX2-U 15); `multiple_64` rainfall_prediction (cue_cost_without_s2_savings, SX2-U 17); `multiple_64` snowfall_prediction (cue_cost_without_s2_savings, SX2-U 17); `multiple_68` google_books_search (cue_cost_without_s2_savings, SX2-U 27); `multiple_68` openlibrary_books_search (cue_cost_without_s2_savings, SX2-U 26); `multiple_72` us_history_population_by_state_year (cue_cost_without_s2_savings, SX2-U 23); `multiple_72` us_economy_gdp_by_state_year (cue_cost_without_s2_savings, SX2-U 20); `multiple_85` basketball_scores_get_scores (cue_cost_without_s2_savings, SX2-U 16); `multiple_85` soccer_scores_get_scores (cue_cost_without_s2_savings, SX2-U 16); `multiple_92` safeway_vegan_products (cue_cost_without_s2_savings, SX2-U 30); `multiple_92` wholefoods_vegan_products (cue_cost_without_s2_savings, SX2-U 30); `multiple_92` walmart_vegan_products (cue_cost_without_s2_savings, SX2-U 29)

## Formative side by side

Paths: `#11 S` is `docs/semantic-audit-pilot/rendered/<id>/S.json`. `#11 X` and `#11 SX` are `docs/semantic-audit-pilot/cue-revision/rendered/<id>/`. `#12` is `docs/official-840/rendered/<id>/`. S2, X2, and SX2 are this packet.

### multiple_35

Exposed. Amendment no-op: `False`.

#### calculate_lcm `/function/description`

U

~~~~
Calculate the least common multiple (lcm) between two integers.
~~~~

#11 S

~~~~
Calculate the least common multiple (lcm) between two integers.
~~~~

#12 S

~~~~
Calculate the least common multiple (lcm) between two integers.
~~~~

S2

~~~~
Calculate the least common multiple (lcm) between two integers.
~~~~

#11 X

~~~~
Calculate the least common multiple (lcm) between two integers. Unlike calculate_gcd, which is the greatest common divisor, this is the least common multiple.
~~~~

#12 X

~~~~
Calculate the least common multiple (lcm) between two integers. Unlike calculate_gcd, which calculates the greatest common divisor, this calculates the least common multiple.
~~~~

X2

~~~~
Calculate the least common multiple (lcm) between two integers. Unlike calculate_gcd, which calculates the greatest common divisor (gcd), this calculates the least common multiple (lcm).
~~~~

#11 SX

~~~~
Calculate the least common multiple (lcm) between two integers. Unlike calculate_gcd, which is the greatest common divisor, this is the least common multiple.
~~~~

#12 SX

~~~~
Calculate the least common multiple (lcm) between two integers. Unlike calculate_gcd, which calculates the greatest common divisor, this calculates the least common multiple.
~~~~

SX2

~~~~
Calculate the least common multiple (lcm) between two integers. Unlike calculate_gcd, which calculates the greatest common divisor (gcd), this calculates the least common multiple (lcm).
~~~~

#### calculate_lcm `/function/parameters/properties/method/description`

U

~~~~
The specific method to use in the calculation. Supported values: 'standard', 'reduced'. Default 'standard'
~~~~

#11 S

~~~~
Calculation method. Supported values: 'standard', 'reduced'. Default 'standard'.
~~~~

#12 S

~~~~
The specific method to use in the calculation. Supported values: 'standard', 'reduced'. Default 'standard'
~~~~

S2

~~~~
The specific method to use in the calculation. Supported values: 'standard', 'reduced'. Default 'standard'
~~~~

#11 X

~~~~
The specific method to use in the calculation. Supported values: 'standard', 'reduced'. Default 'standard'
~~~~

#12 X

~~~~
The specific method to use in the calculation. Supported values: 'standard', 'reduced'. Default 'standard'
~~~~

X2

~~~~
The specific method to use in the calculation. Supported values: 'standard', 'reduced'. Default 'standard'
~~~~

#11 SX

~~~~
Calculation method. Supported values: 'standard', 'reduced'. Default 'standard'.
~~~~

#12 SX

~~~~
The specific method to use in the calculation. Supported values: 'standard', 'reduced'. Default 'standard'
~~~~

SX2

~~~~
The specific method to use in the calculation. Supported values: 'standard', 'reduced'. Default 'standard'
~~~~

#### calculate_gcd `/function/description`

U

~~~~
Calculate the greatest common divisor (gcd) between two integers.
~~~~

#11 S

~~~~
Calculate the greatest common divisor (gcd) between two integers.
~~~~

#12 S

~~~~
Calculate the greatest common divisor (gcd) between two integers.
~~~~

S2

~~~~
Calculate the greatest common divisor (gcd) between two integers.
~~~~

#11 X

~~~~
Calculate the greatest common divisor (gcd) between two integers. Unlike calculate_lcm, which is the least common multiple, this is the greatest common divisor.
~~~~

#12 X

~~~~
Calculate the greatest common divisor (gcd) between two integers. Unlike calculate_lcm, which calculates the least common multiple, this calculates the greatest common divisor.
~~~~

X2

~~~~
Calculate the greatest common divisor (gcd) between two integers. Unlike calculate_lcm, which calculates the least common multiple (lcm), this calculates the greatest common divisor (gcd).
~~~~

#11 SX

~~~~
Calculate the greatest common divisor (gcd) between two integers. Unlike calculate_lcm, which is the least common multiple, this is the greatest common divisor.
~~~~

#12 SX

~~~~
Calculate the greatest common divisor (gcd) between two integers. Unlike calculate_lcm, which calculates the least common multiple, this calculates the greatest common divisor.
~~~~

SX2

~~~~
Calculate the greatest common divisor (gcd) between two integers. Unlike calculate_lcm, which calculates the least common multiple (lcm), this calculates the greatest common divisor (gcd).
~~~~

#### calculate_gcd `/function/parameters/properties/algorithm/description`

U

~~~~
The specific algorithm to use in the calculation. Supported values: 'euclidean', 'binary'. Default 'euclidean'
~~~~

#11 S

~~~~
Calculation algorithm. Default 'euclidean'.
~~~~

#12 S

~~~~
The specific algorithm to use in the calculation. Supported values: 'euclidean', 'binary'. Default 'euclidean'
~~~~

S2

~~~~
The specific algorithm to use in the calculation. Default 'euclidean'
~~~~

#11 X

~~~~
The specific algorithm to use in the calculation. Supported values: 'euclidean', 'binary'. Default 'euclidean'
~~~~

#12 X

~~~~
The specific algorithm to use in the calculation. Supported values: 'euclidean', 'binary'. Default 'euclidean'
~~~~

X2

~~~~
The specific algorithm to use in the calculation. Supported values: 'euclidean', 'binary'. Default 'euclidean'
~~~~

#11 SX

~~~~
Calculation algorithm. Default 'euclidean'.
~~~~

#12 SX

~~~~
The specific algorithm to use in the calculation. Supported values: 'euclidean', 'binary'. Default 'euclidean'
~~~~

SX2

~~~~
The specific algorithm to use in the calculation. Default 'euclidean'
~~~~

### multiple_0

Exposed. Amendment no-op: `False`.

#### triangle_properties_get `/function/description`

U

~~~~
Retrieve the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given.
~~~~

#11 S

~~~~
Retrieve a triangle's dimensions, such as area and perimeter, given three side lengths.
~~~~

#12 S

~~~~
Retrieve the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given.
~~~~

S2

~~~~
Retrieve the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given.
~~~~

#11 X

~~~~
Retrieve the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given. Unlike circle_properties_get, which takes a radius, this takes the lengths of three sides.
~~~~

#12 X

~~~~
Retrieve the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given. Unlike circle_properties_get, which retrieves the area and circumference of a circle, this retrieves the area and perimeter of a triangle.
~~~~

X2

~~~~
Retrieve the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given.
~~~~

#11 SX

~~~~
Retrieve a triangle's dimensions, such as area and perimeter, given three side lengths. Unlike circle_properties_get, which takes a radius, this takes the lengths of three sides.
~~~~

#12 SX

~~~~
Retrieve the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given. Unlike circle_properties_get, which retrieves the area and circumference of a circle, this retrieves the area and perimeter of a triangle.
~~~~

SX2

~~~~
Retrieve the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given.
~~~~

#### triangle_properties_get `/function/parameters/properties/side1/description`

U

~~~~
The length of first side of the triangle.
~~~~

#11 S

~~~~
Length of the first side.
~~~~

#12 S

~~~~
The length of first side of the triangle.
~~~~

S2

~~~~
The length of first side of the triangle.
~~~~

#11 X

~~~~
The length of first side of the triangle.
~~~~

#12 X

~~~~
The length of first side of the triangle.
~~~~

X2

~~~~
The length of first side of the triangle.
~~~~

#11 SX

~~~~
Length of the first side.
~~~~

#12 SX

~~~~
The length of first side of the triangle.
~~~~

SX2

~~~~
The length of first side of the triangle.
~~~~

#### triangle_properties_get `/function/parameters/properties/side2/description`

U

~~~~
The length of second side of the triangle.
~~~~

#11 S

~~~~
Length of the second side.
~~~~

#12 S

~~~~
The length of second side of the triangle.
~~~~

S2

~~~~
The length of second side of the triangle.
~~~~

#11 X

~~~~
The length of second side of the triangle.
~~~~

#12 X

~~~~
The length of second side of the triangle.
~~~~

X2

~~~~
The length of second side of the triangle.
~~~~

#11 SX

~~~~
Length of the second side.
~~~~

#12 SX

~~~~
The length of second side of the triangle.
~~~~

SX2

~~~~
The length of second side of the triangle.
~~~~

#### triangle_properties_get `/function/parameters/properties/side3/description`

U

~~~~
The length of third side of the triangle.
~~~~

#11 S

~~~~
Length of the third side.
~~~~

#12 S

~~~~
The length of third side of the triangle.
~~~~

S2

~~~~
The length of third side of the triangle.
~~~~

#11 X

~~~~
The length of third side of the triangle.
~~~~

#12 X

~~~~
The length of third side of the triangle.
~~~~

X2

~~~~
The length of third side of the triangle.
~~~~

#11 SX

~~~~
Length of the third side.
~~~~

#12 SX

~~~~
The length of third side of the triangle.
~~~~

SX2

~~~~
The length of third side of the triangle.
~~~~

#### triangle_properties_get `/function/parameters/properties/get_area/description`

U

~~~~
A flag to determine whether to calculate the area of triangle. Default is true.
~~~~

#11 S

~~~~
Whether to calculate the area.
~~~~

#12 S

~~~~
A flag to determine whether to calculate the area of triangle.
~~~~

S2

~~~~
Whether to calculate the area
~~~~

#11 X

~~~~
A flag to determine whether to calculate the area of triangle. Default is true.
~~~~

#12 X

~~~~
A flag to determine whether to calculate the area of triangle. Default is true.
~~~~

X2

~~~~
A flag to determine whether to calculate the area of triangle. Default is true.
~~~~

#11 SX

~~~~
Whether to calculate the area.
~~~~

#12 SX

~~~~
A flag to determine whether to calculate the area of triangle.
~~~~

SX2

~~~~
Whether to calculate the area
~~~~

#### triangle_properties_get `/function/parameters/properties/get_perimeter/description`

U

~~~~
A flag to determine whether to calculate the perimeter of triangle. Default is true.
~~~~

#11 S

~~~~
Whether to calculate the perimeter.
~~~~

#12 S

~~~~
A flag to determine whether to calculate the perimeter of triangle.
~~~~

S2

~~~~
Whether to calculate the perimeter
~~~~

#11 X

~~~~
A flag to determine whether to calculate the perimeter of triangle. Default is true.
~~~~

#12 X

~~~~
A flag to determine whether to calculate the perimeter of triangle. Default is true.
~~~~

X2

~~~~
A flag to determine whether to calculate the perimeter of triangle. Default is true.
~~~~

#11 SX

~~~~
Whether to calculate the perimeter.
~~~~

#12 SX

~~~~
A flag to determine whether to calculate the perimeter of triangle.
~~~~

SX2

~~~~
Whether to calculate the perimeter
~~~~

#### triangle_properties_get `/function/parameters/properties/get_angles/description`

U

~~~~
A flag to determine whether to calculate the internal angles of triangle. Default is true.
~~~~

#11 S

~~~~
Whether to calculate the internal angles.
~~~~

#12 S

~~~~
A flag to determine whether to calculate the internal angles of triangle.
~~~~

S2

~~~~
Whether to calculate the internal angles
~~~~

#11 X

~~~~
A flag to determine whether to calculate the internal angles of triangle. Default is true.
~~~~

#12 X

~~~~
A flag to determine whether to calculate the internal angles of triangle. Default is true.
~~~~

X2

~~~~
A flag to determine whether to calculate the internal angles of triangle. Default is true.
~~~~

#11 SX

~~~~
Whether to calculate the internal angles.
~~~~

#12 SX

~~~~
A flag to determine whether to calculate the internal angles of triangle.
~~~~

SX2

~~~~
Whether to calculate the internal angles
~~~~

#### circle_properties_get `/function/description`

U

~~~~
Retrieve the dimensions, such as area and circumference, of a circle if radius is given.
~~~~

#11 S

~~~~
Retrieve a circle's dimensions, such as area and circumference, given its radius.
~~~~

#12 S

~~~~
Retrieve the dimensions, such as area and circumference, of a circle if radius is given.
~~~~

S2

~~~~
Retrieve the dimensions, such as area and circumference, of a circle if radius is given.
~~~~

#11 X

~~~~
Retrieve the dimensions, such as area and circumference, of a circle if radius is given. Unlike triangle_properties_get, which takes the lengths of three sides, this takes a radius.
~~~~

#12 X

~~~~
Retrieve the dimensions, such as area and circumference, of a circle if radius is given. Unlike triangle_properties_get, which retrieves the area and perimeter of a triangle, this retrieves the area and circumference of a circle.
~~~~

X2

~~~~
Retrieve the dimensions, such as area and circumference, of a circle if radius is given.
~~~~

#11 SX

~~~~
Retrieve a circle's dimensions, such as area and circumference, given its radius. Unlike triangle_properties_get, which takes the lengths of three sides, this takes a radius.
~~~~

#12 SX

~~~~
Retrieve the dimensions, such as area and circumference, of a circle if radius is given. Unlike triangle_properties_get, which retrieves the area and perimeter of a triangle, this retrieves the area and circumference of a circle.
~~~~

SX2

~~~~
Retrieve the dimensions, such as area and circumference, of a circle if radius is given.
~~~~

#### circle_properties_get `/function/parameters/properties/radius/description`

U

~~~~
The length of radius of the circle. This is a float type value.
~~~~

#11 S

~~~~
The length of radius of the circle. This is a float type value.
~~~~

#12 S

~~~~
The length of radius of the circle. This is a float type value.
~~~~

S2

~~~~
The length of radius of the circle.
~~~~

#11 X

~~~~
The length of radius of the circle. This is a float type value.
~~~~

#12 X

~~~~
The length of radius of the circle. This is a float type value.
~~~~

X2

~~~~
The length of radius of the circle. This is a float type value.
~~~~

#11 SX

~~~~
The length of radius of the circle. This is a float type value.
~~~~

#12 SX

~~~~
The length of radius of the circle. This is a float type value.
~~~~

SX2

~~~~
The length of radius of the circle.
~~~~

#### circle_properties_get `/function/parameters/properties/get_area/description`

U

~~~~
A flag to determine whether to calculate the area of circle. Default is true.
~~~~

#11 S

~~~~
Whether to calculate the area.
~~~~

#12 S

~~~~
A flag to determine whether to calculate the area of circle.
~~~~

S2

~~~~
Whether to calculate the area
~~~~

#11 X

~~~~
A flag to determine whether to calculate the area of circle. Default is true.
~~~~

#12 X

~~~~
A flag to determine whether to calculate the area of circle. Default is true.
~~~~

X2

~~~~
A flag to determine whether to calculate the area of circle. Default is true.
~~~~

#11 SX

~~~~
Whether to calculate the area.
~~~~

#12 SX

~~~~
A flag to determine whether to calculate the area of circle.
~~~~

SX2

~~~~
Whether to calculate the area
~~~~

#### circle_properties_get `/function/parameters/properties/get_circumference/description`

U

~~~~
A flag to determine whether to calculate the circumference of circle. Default is true.
~~~~

#11 S

~~~~
Whether to calculate the circumference.
~~~~

#12 S

~~~~
A flag to determine whether to calculate the circumference of circle.
~~~~

S2

~~~~
Whether to calculate the circumference
~~~~

#11 X

~~~~
A flag to determine whether to calculate the circumference of circle. Default is true.
~~~~

#12 X

~~~~
A flag to determine whether to calculate the circumference of circle. Default is true.
~~~~

X2

~~~~
A flag to determine whether to calculate the circumference of circle. Default is true.
~~~~

#11 SX

~~~~
Whether to calculate the circumference.
~~~~

#12 SX

~~~~
A flag to determine whether to calculate the circumference of circle.
~~~~

SX2

~~~~
Whether to calculate the circumference
~~~~

### multiple_11

Exposed. Amendment no-op: `False`.

#### math_roots_quadratic `/function/description`

U

~~~~
Calculate the roots of a quadratic equation.
~~~~

#11 S

~~~~
Calculate the roots of a quadratic equation.
~~~~

#12 S

~~~~
Calculate the roots of a quadratic equation.
~~~~

S2

~~~~
Calculate the roots of a quadratic equation.
~~~~

#11 X

~~~~
Calculate the roots of a quadratic equation. Unlike math_roots_cubic, which takes four separate coefficients of a cubic, this takes three separate coefficients of a quadratic.
~~~~

#12 X

~~~~
Calculate the roots of a quadratic equation.
~~~~

X2

~~~~
Calculate the roots of a quadratic equation. Unlike math_roots_polynomial, which takes an ordered coefficient array, this takes named quadratic coefficients.
~~~~

#11 SX

~~~~
Calculate the roots of a quadratic equation. Unlike math_roots_cubic, which takes four separate coefficients of a cubic, this takes three separate coefficients of a quadratic.
~~~~

#12 SX

~~~~
Calculate the roots of a quadratic equation.
~~~~

SX2

~~~~
Calculate the roots of a quadratic equation. Unlike math_roots_polynomial, which takes an ordered coefficient array, this takes named quadratic coefficients.
~~~~

#### math_roots_cubic `/function/description`

U

~~~~
Calculate the roots of a cubic equation.
~~~~

#11 S

~~~~
Calculate the roots of a cubic equation.
~~~~

#12 S

~~~~
Calculate the roots of a cubic equation.
~~~~

S2

~~~~
Calculate the roots of a cubic equation.
~~~~

#11 X

~~~~
Calculate the roots of a cubic equation. Unlike math_roots_quadratic, which takes three separate coefficients of a quadratic, this takes four separate coefficients of a cubic.
~~~~

#12 X

~~~~
Calculate the roots of a cubic equation.
~~~~

X2

~~~~
Calculate the roots of a cubic equation. Unlike math_roots_polynomial, which takes an ordered coefficient array, this takes named cubic coefficients.
~~~~

#11 SX

~~~~
Calculate the roots of a cubic equation. Unlike math_roots_quadratic, which takes three separate coefficients of a quadratic, this takes four separate coefficients of a cubic.
~~~~

#12 SX

~~~~
Calculate the roots of a cubic equation.
~~~~

SX2

~~~~
Calculate the roots of a cubic equation. Unlike math_roots_polynomial, which takes an ordered coefficient array, this takes named cubic coefficients.
~~~~

#### math_roots_cubic `/function/parameters/properties/a/description`

U

~~~~
Coefficient of the third-degree term. This is a float type value.
~~~~

#11 S

~~~~
Coefficient of the third-degree term. This is a float type value.
~~~~

#12 S

~~~~
Coefficient of the third-degree term. This is a float type value.
~~~~

S2

~~~~
Coefficient of the third-degree term.
~~~~

#11 X

~~~~
Coefficient of the third-degree term. This is a float type value.
~~~~

#12 X

~~~~
Coefficient of the third-degree term. This is a float type value.
~~~~

X2

~~~~
Coefficient of the third-degree term. This is a float type value.
~~~~

#11 SX

~~~~
Coefficient of the third-degree term. This is a float type value.
~~~~

#12 SX

~~~~
Coefficient of the third-degree term. This is a float type value.
~~~~

SX2

~~~~
Coefficient of the third-degree term.
~~~~

#### math_roots_cubic `/function/parameters/properties/b/description`

U

~~~~
Coefficient of the second-degree term. This is a float type value.
~~~~

#11 S

~~~~
Coefficient of the second-degree term. This is a float type value.
~~~~

#12 S

~~~~
Coefficient of the second-degree term. This is a float type value.
~~~~

S2

~~~~
Coefficient of the second-degree term.
~~~~

#11 X

~~~~
Coefficient of the second-degree term. This is a float type value.
~~~~

#12 X

~~~~
Coefficient of the second-degree term. This is a float type value.
~~~~

X2

~~~~
Coefficient of the second-degree term. This is a float type value.
~~~~

#11 SX

~~~~
Coefficient of the second-degree term. This is a float type value.
~~~~

#12 SX

~~~~
Coefficient of the second-degree term. This is a float type value.
~~~~

SX2

~~~~
Coefficient of the second-degree term.
~~~~

#### math_roots_cubic `/function/parameters/properties/c/description`

U

~~~~
Coefficient of the first-degree term. This is a float type value.
~~~~

#11 S

~~~~
Coefficient of the first-degree term. This is a float type value.
~~~~

#12 S

~~~~
Coefficient of the first-degree term. This is a float type value.
~~~~

S2

~~~~
Coefficient of the first-degree term.
~~~~

#11 X

~~~~
Coefficient of the first-degree term. This is a float type value.
~~~~

#12 X

~~~~
Coefficient of the first-degree term. This is a float type value.
~~~~

X2

~~~~
Coefficient of the first-degree term. This is a float type value.
~~~~

#11 SX

~~~~
Coefficient of the first-degree term. This is a float type value.
~~~~

#12 SX

~~~~
Coefficient of the first-degree term. This is a float type value.
~~~~

SX2

~~~~
Coefficient of the first-degree term.
~~~~

#### math_roots_cubic `/function/parameters/properties/d/description`

U

~~~~
Constant term. This is a float type value.
~~~~

#11 S

~~~~
Constant term. This is a float type value.
~~~~

#12 S

~~~~
Constant term. This is a float type value.
~~~~

S2

~~~~
Constant term.
~~~~

#11 X

~~~~
Constant term. This is a float type value.
~~~~

#12 X

~~~~
Constant term. This is a float type value.
~~~~

X2

~~~~
Constant term. This is a float type value.
~~~~

#11 SX

~~~~
Constant term. This is a float type value.
~~~~

#12 SX

~~~~
Constant term. This is a float type value.
~~~~

SX2

~~~~
Constant term.
~~~~

#### math_roots_polynomial `/function/description`

U

~~~~
Calculate the roots of a polynomial equation.
~~~~

#11 S

~~~~
Calculate the roots of a polynomial equation.
~~~~

#12 S

~~~~
Calculate the roots of a polynomial equation.
~~~~

S2

~~~~
Calculate the roots of a polynomial equation.
~~~~

#11 X

~~~~
Calculate the roots of a polynomial equation. Unlike math_roots_quadratic, which takes separate a, b, and c arguments, this takes a coefficient array in highest-degree-first order.
~~~~

#12 X

~~~~
Calculate the roots of a polynomial equation.
~~~~

X2

~~~~
Calculate the roots of a polynomial equation. Unlike math_roots_quadratic, which takes named quadratic coefficients, this takes an ordered coefficient array.
~~~~

#11 SX

~~~~
Calculate the roots of a polynomial equation. Unlike math_roots_quadratic, which takes separate a, b, and c arguments, this takes a coefficient array in highest-degree-first order.
~~~~

#12 SX

~~~~
Calculate the roots of a polynomial equation.
~~~~

SX2

~~~~
Calculate the roots of a polynomial equation. Unlike math_roots_quadratic, which takes named quadratic coefficients, this takes an ordered coefficient array.
~~~~

#### math_roots_polynomial `/function/parameters/properties/coefficients/description`

U

~~~~
Array of coefficients of the polynomial equation starting from highest degree term.
~~~~

#11 S

~~~~
Coefficients, starting from the highest-degree term.
~~~~

#12 S

~~~~
Array of coefficients of the polynomial equation starting from highest degree term.
~~~~

S2

~~~~
Array of coefficients of the polynomial equation starting from highest degree term.
~~~~

#11 X

~~~~
Array of coefficients of the polynomial equation starting from highest degree term.
~~~~

#12 X

~~~~
Array of coefficients of the polynomial equation starting from highest degree term.
~~~~

X2

~~~~
Array of coefficients of the polynomial equation starting from highest degree term.
~~~~

#11 SX

~~~~
Coefficients, starting from the highest-degree term.
~~~~

#12 SX

~~~~
Array of coefficients of the polynomial equation starting from highest degree term.
~~~~

SX2

~~~~
Array of coefficients of the polynomial equation starting from highest degree term.
~~~~

### multiple_12

Exposed. Amendment no-op: `False`.

#### corporate_finance_calculate_YOY_growth_rate `/function/description`

U

~~~~
Calculate the year over year (YOY) growth rate for a company.
~~~~

#11 S

~~~~
Calculate the year over year (YOY) growth rate for a company.
~~~~

#12 S

~~~~
Calculate the year over year (YOY) growth rate for a company.
~~~~

S2

~~~~
Calculate the year over year (YOY) growth rate for a company.
~~~~

#11 X

~~~~
Calculate the year over year (YOY) growth rate for a company. Unlike financial_ratios_calculate_ROE, which uses net income and average shareholder equity, this uses revenue from an initial year and a subsequent year.
~~~~

#12 X

~~~~
Calculate the year over year (YOY) growth rate for a company. Unlike financial_ratios_calculate_ROE, which calculates the return on equity, this calculates the year over year growth rate.
~~~~

X2

~~~~
Calculate the year over year (YOY) growth rate for a company.
~~~~

#11 SX

~~~~
Calculate the year over year (YOY) growth rate for a company. Unlike financial_ratios_calculate_ROE, which uses net income and average shareholder equity, this uses revenue from an initial year and a subsequent year.
~~~~

#12 SX

~~~~
Calculate the year over year (YOY) growth rate for a company. Unlike financial_ratios_calculate_ROE, which calculates the return on equity, this calculates the year over year growth rate.
~~~~

SX2

~~~~
Calculate the year over year (YOY) growth rate for a company.
~~~~

#### corporate_finance_calculate_YOY_growth_rate `/function/parameters/properties/company_name/description`

U

~~~~
The name of the company for which to calculate the YOY growth rate.
~~~~

#11 S

~~~~
Company name.
~~~~

#12 S

~~~~
The name of the company for which to calculate the YOY growth rate.
~~~~

S2

~~~~
The name of the company.
~~~~

#11 X

~~~~
The name of the company for which to calculate the YOY growth rate.
~~~~

#12 X

~~~~
The name of the company for which to calculate the YOY growth rate.
~~~~

X2

~~~~
The name of the company for which to calculate the YOY growth rate.
~~~~

#11 SX

~~~~
Company name.
~~~~

#12 SX

~~~~
The name of the company for which to calculate the YOY growth rate.
~~~~

SX2

~~~~
The name of the company.
~~~~

#### financial_ratios_calculate_ROE `/function/description`

U

~~~~
Calculate the return on equity (ROE) for a company.
~~~~

#11 S

~~~~
Calculate the return on equity (ROE) for a company.
~~~~

#12 S

~~~~
Calculate the return on equity (ROE) for a company.
~~~~

S2

~~~~
Calculate the return on equity (ROE) for a company.
~~~~

#11 X

~~~~
Calculate the return on equity (ROE) for a company. Unlike financial_ratios_calculate_ROA, whose denominator is total average assets, this uses average shareholder equity as its denominator.
~~~~

#12 X

~~~~
Calculate the return on equity (ROE) for a company. Unlike financial_ratios_calculate_ROA, which calculates the return on assets from total average assets, this calculates the return on equity from average shareholder equity.
~~~~

X2

~~~~
Calculate the return on equity (ROE) for a company.
~~~~

#11 SX

~~~~
Calculate the return on equity (ROE) for a company. Unlike financial_ratios_calculate_ROA, whose denominator is total average assets, this uses average shareholder equity as its denominator.
~~~~

#12 SX

~~~~
Calculate the return on equity (ROE) for a company. Unlike financial_ratios_calculate_ROA, which calculates the return on assets from total average assets, this calculates the return on equity from average shareholder equity.
~~~~

SX2

~~~~
Calculate the return on equity (ROE) for a company.
~~~~

#### financial_ratios_calculate_ROE `/function/parameters/properties/net_income/description`

U

~~~~
Net income for the period. This is a float type value.
~~~~

#11 S

~~~~
Net income for the period. This is a float type value.
~~~~

#12 S

~~~~
Net income for the period. This is a float type value.
~~~~

S2

~~~~
Net income for the period.
~~~~

#11 X

~~~~
Net income for the period. This is a float type value.
~~~~

#12 X

~~~~
Net income for the period. This is a float type value.
~~~~

X2

~~~~
Net income for the period. This is a float type value.
~~~~

#11 SX

~~~~
Net income for the period. This is a float type value.
~~~~

#12 SX

~~~~
Net income for the period. This is a float type value.
~~~~

SX2

~~~~
Net income for the period.
~~~~

#### financial_ratios_calculate_ROE `/function/parameters/properties/shareholder_equity/description`

U

~~~~
Average shareholder equity for the period. This is a float type value.
~~~~

#11 S

~~~~
Average shareholder equity for the period. This is a float type value.
~~~~

#12 S

~~~~
Average shareholder equity for the period. This is a float type value.
~~~~

S2

~~~~
Average shareholder equity for the period.
~~~~

#11 X

~~~~
Average shareholder equity for the period. This is a float type value.
~~~~

#12 X

~~~~
Average shareholder equity for the period. This is a float type value.
~~~~

X2

~~~~
Average shareholder equity for the period. This is a float type value.
~~~~

#11 SX

~~~~
Average shareholder equity for the period. This is a float type value.
~~~~

#12 SX

~~~~
Average shareholder equity for the period. This is a float type value.
~~~~

SX2

~~~~
Average shareholder equity for the period.
~~~~

#### financial_ratios_calculate_ROA `/function/description`

U

~~~~
Calculate the return on assets (ROA) for a company.
~~~~

#11 S

~~~~
Calculate the return on assets (ROA) for a company.
~~~~

#12 S

~~~~
Calculate the return on assets (ROA) for a company.
~~~~

S2

~~~~
Calculate the return on assets (ROA) for a company.
~~~~

#11 X

~~~~
Calculate the return on assets (ROA) for a company. Unlike financial_ratios_calculate_ROE, whose denominator is average shareholder equity, this uses total average assets as its denominator.
~~~~

#12 X

~~~~
Calculate the return on assets (ROA) for a company. Unlike financial_ratios_calculate_ROE, which calculates the return on equity from average shareholder equity, this calculates the return on assets from total average assets.
~~~~

X2

~~~~
Calculate the return on assets (ROA) for a company.
~~~~

#11 SX

~~~~
Calculate the return on assets (ROA) for a company. Unlike financial_ratios_calculate_ROE, whose denominator is average shareholder equity, this uses total average assets as its denominator.
~~~~

#12 SX

~~~~
Calculate the return on assets (ROA) for a company. Unlike financial_ratios_calculate_ROE, which calculates the return on equity from average shareholder equity, this calculates the return on assets from total average assets.
~~~~

SX2

~~~~
Calculate the return on assets (ROA) for a company.
~~~~

#### financial_ratios_calculate_ROA `/function/parameters/properties/net_income/description`

U

~~~~
Net income for the period. This is a float type value.
~~~~

#11 S

~~~~
Net income for the period. This is a float type value.
~~~~

#12 S

~~~~
Net income for the period. This is a float type value.
~~~~

S2

~~~~
Net income for the period.
~~~~

#11 X

~~~~
Net income for the period. This is a float type value.
~~~~

#12 X

~~~~
Net income for the period. This is a float type value.
~~~~

X2

~~~~
Net income for the period. This is a float type value.
~~~~

#11 SX

~~~~
Net income for the period. This is a float type value.
~~~~

#12 SX

~~~~
Net income for the period. This is a float type value.
~~~~

SX2

~~~~
Net income for the period.
~~~~

#### financial_ratios_calculate_ROA `/function/parameters/properties/total_assets/description`

U

~~~~
Total average assets for the period. This is a float type value.
~~~~

#11 S

~~~~
Total average assets for the period. This is a float type value.
~~~~

#12 S

~~~~
Total average assets for the period. This is a float type value.
~~~~

S2

~~~~
Total average assets for the period.
~~~~

#11 X

~~~~
Total average assets for the period. This is a float type value.
~~~~

#12 X

~~~~
Total average assets for the period. This is a float type value.
~~~~

X2

~~~~
Total average assets for the period. This is a float type value.
~~~~

#11 SX

~~~~
Total average assets for the period. This is a float type value.
~~~~

#12 SX

~~~~
Total average assets for the period. This is a float type value.
~~~~

SX2

~~~~
Total average assets for the period.
~~~~

### multiple_7

Exposed. Amendment no-op: `True`.

#### wildlife_population_assess_growth `/function/description`

U

~~~~
Assesses the population growth of a specific species in a specified location over a period.
~~~~

#11 S

~~~~
Assesses a species' population growth at a location over a period.
~~~~

#12 S

~~~~
Assesses the population growth of a specific species in a specified location over a period.
~~~~

S2

~~~~
Assesses the population growth of a specific species in a specified location over a period.
~~~~

#11 X

~~~~
Assesses the population growth of a specific species in a specified location over a period. Unlike ecological_impact_analyze, which analyzes impact on a particular ecosystem, this assesses population growth.
~~~~

#12 X

~~~~
Assesses the population growth of a specific species in a specified location over a period.
~~~~

X2

~~~~
Assesses the population growth of a specific species in a specified location over a period.
~~~~

#11 SX

~~~~
Assesses a species' population growth at a location over a period. Unlike ecological_impact_analyze, which analyzes impact on a particular ecosystem, this assesses population growth.
~~~~

#12 SX

~~~~
Assesses the population growth of a specific species in a specified location over a period.
~~~~

SX2

~~~~
Assesses the population growth of a specific species in a specified location over a period.
~~~~

#### wildlife_population_assess_growth `/function/parameters/properties/species/description`

U

~~~~
The species for which the growth is to be calculated.
~~~~

#11 S

~~~~
Species whose growth is calculated.
~~~~

#12 S

~~~~
The species for which the growth is to be calculated.
~~~~

S2

~~~~
The species for which the growth is to be calculated.
~~~~

#11 X

~~~~
The species for which the growth is to be calculated.
~~~~

#12 X

~~~~
The species for which the growth is to be calculated.
~~~~

X2

~~~~
The species for which the growth is to be calculated.
~~~~

#11 SX

~~~~
Species whose growth is calculated.
~~~~

#12 SX

~~~~
The species for which the growth is to be calculated.
~~~~

SX2

~~~~
The species for which the growth is to be calculated.
~~~~

#### wildlife_population_assess_growth `/function/parameters/properties/duration/description`

U

~~~~
The time period for which the population growth should be calculated in years.
~~~~

#11 S

~~~~
Time period in years.
~~~~

#12 S

~~~~
The time period for which the population growth should be calculated in years.
~~~~

S2

~~~~
The time period for which the population growth should be calculated in years.
~~~~

#11 X

~~~~
The time period for which the population growth should be calculated in years.
~~~~

#12 X

~~~~
The time period for which the population growth should be calculated in years.
~~~~

X2

~~~~
The time period for which the population growth should be calculated in years.
~~~~

#11 SX

~~~~
Time period in years.
~~~~

#12 SX

~~~~
The time period for which the population growth should be calculated in years.
~~~~

SX2

~~~~
The time period for which the population growth should be calculated in years.
~~~~

#### ecological_impact_analyze `/function/description`

U

~~~~
Analyzes the impact of a species on a particular ecosystem.
~~~~

#11 S

~~~~
Analyzes the impact of a species on a particular ecosystem.
~~~~

#12 S

~~~~
Analyzes the impact of a species on a particular ecosystem.
~~~~

S2

~~~~
Analyzes the impact of a species on a particular ecosystem.
~~~~

#11 X

~~~~
Analyzes the impact of a species on a particular ecosystem. Unlike wildlife_population_assess_growth, which assesses population growth, this analyzes impact on a particular ecosystem.
~~~~

#12 X

~~~~
Analyzes the impact of a species on a particular ecosystem.
~~~~

X2

~~~~
Analyzes the impact of a species on a particular ecosystem.
~~~~

#11 SX

~~~~
Analyzes the impact of a species on a particular ecosystem. Unlike wildlife_population_assess_growth, which assesses population growth, this analyzes impact on a particular ecosystem.
~~~~

#12 SX

~~~~
Analyzes the impact of a species on a particular ecosystem.
~~~~

SX2

~~~~
Analyzes the impact of a species on a particular ecosystem.
~~~~

#### ecological_impact_analyze `/function/parameters/properties/timeframe/description`

U

~~~~
The time period for which the impact analysis should be carried out in years.
~~~~

#11 S

~~~~
Time period in years.
~~~~

#12 S

~~~~
The time period for which the impact analysis should be carried out in years.
~~~~

S2

~~~~
The time period for which the impact analysis should be carried out in years.
~~~~

#11 X

~~~~
The time period for which the impact analysis should be carried out in years.
~~~~

#12 X

~~~~
The time period for which the impact analysis should be carried out in years.
~~~~

X2

~~~~
The time period for which the impact analysis should be carried out in years.
~~~~

#11 SX

~~~~
Time period in years.
~~~~

#12 SX

~~~~
The time period for which the impact analysis should be carried out in years.
~~~~

SX2

~~~~
The time period for which the impact analysis should be carried out in years.
~~~~

### multiple_92

Exposed. Amendment no-op: `False`.

#### safeway_vegan_products `/function/description`

U

~~~~
Get available vegan products at specified Safeway store
~~~~

#11 S

~~~~
Get available vegan products at specified Safeway store
~~~~

#12 S

~~~~
Get available vegan products at specified Safeway store
~~~~

S2

~~~~
Get available vegan products at specified Safeway store
~~~~

#11 X

~~~~
Get available vegan products at specified Safeway store Unlike wholefoods_vegan_products, which names a Whole Foods store, this names a Safeway store.
~~~~

#12 X

~~~~
Get available vegan products at specified Safeway store Unlike wholefoods_vegan_products, which gets vegan products at a Whole Foods store, this gets vegan products at a Safeway store.
~~~~

X2

~~~~
Get available vegan products at specified Safeway store Unlike wholefoods_vegan_products, which gets available vegan products at specified Whole Foods store, this gets available vegan products at specified Safeway store.
~~~~

#11 SX

~~~~
Get available vegan products at specified Safeway store Unlike wholefoods_vegan_products, which names a Whole Foods store, this names a Safeway store.
~~~~

#12 SX

~~~~
Get available vegan products at specified Safeway store Unlike wholefoods_vegan_products, which gets vegan products at a Whole Foods store, this gets vegan products at a Safeway store.
~~~~

SX2

~~~~
Get available vegan products at specified Safeway store Unlike wholefoods_vegan_products, which gets available vegan products at specified Whole Foods store, this gets available vegan products at specified Safeway store.
~~~~

#### wholefoods_vegan_products `/function/description`

U

~~~~
Get available vegan products at specified Whole Foods store
~~~~

#11 S

~~~~
Get available vegan products at specified Whole Foods store
~~~~

#12 S

~~~~
Get available vegan products at specified Whole Foods store
~~~~

S2

~~~~
Get available vegan products at specified Whole Foods store
~~~~

#11 X

~~~~
Get available vegan products at specified Whole Foods store Unlike safeway_vegan_products, which names a Safeway store, this names a Whole Foods store.
~~~~

#12 X

~~~~
Get available vegan products at specified Whole Foods store Unlike safeway_vegan_products, which gets vegan products at a Safeway store, this gets vegan products at a Whole Foods store.
~~~~

X2

~~~~
Get available vegan products at specified Whole Foods store Unlike safeway_vegan_products, which gets available vegan products at specified Safeway store, this gets available vegan products at specified Whole Foods store.
~~~~

#11 SX

~~~~
Get available vegan products at specified Whole Foods store Unlike safeway_vegan_products, which names a Safeway store, this names a Whole Foods store.
~~~~

#12 SX

~~~~
Get available vegan products at specified Whole Foods store Unlike safeway_vegan_products, which gets vegan products at a Safeway store, this gets vegan products at a Whole Foods store.
~~~~

SX2

~~~~
Get available vegan products at specified Whole Foods store Unlike safeway_vegan_products, which gets available vegan products at specified Safeway store, this gets available vegan products at specified Whole Foods store.
~~~~

#### walmart_vegan_products `/function/description`

U

~~~~
Get available vegan products at specified Walmart store
~~~~

#11 S

~~~~
Get available vegan products at specified Walmart store
~~~~

#12 S

~~~~
Get available vegan products at specified Walmart store
~~~~

S2

~~~~
Get available vegan products at specified Walmart store
~~~~

#11 X

~~~~
Get available vegan products at specified Walmart store Unlike safeway_vegan_products, which names a Safeway store, this names a Walmart store.
~~~~

#12 X

~~~~
Get available vegan products at specified Walmart store Unlike safeway_vegan_products, which gets vegan products at a Safeway store, this gets vegan products at a Walmart store.
~~~~

X2

~~~~
Get available vegan products at specified Walmart store Unlike safeway_vegan_products, which gets available vegan products at specified Safeway store, this gets available vegan products at specified Walmart store.
~~~~

#11 SX

~~~~
Get available vegan products at specified Walmart store Unlike safeway_vegan_products, which names a Safeway store, this names a Walmart store.
~~~~

#12 SX

~~~~
Get available vegan products at specified Walmart store Unlike safeway_vegan_products, which gets vegan products at a Safeway store, this gets vegan products at a Walmart store.
~~~~

SX2

~~~~
Get available vegan products at specified Walmart store Unlike safeway_vegan_products, which gets available vegan products at specified Safeway store, this gets available vegan products at specified Walmart store.
~~~~

### multiple_153

Exposed. Amendment no-op: `False`.

#### locate_tallest_mountains `/function/parameters/properties/radius/description`

U

~~~~
The radius within which to find mountains, measured in kilometers. This is a float type value.
~~~~

#11 S

~~~~
The radius within which to find mountains, measured in kilometers. This is a float type value.
~~~~

#12 S

~~~~
The radius within which to find mountains, measured in kilometers. This is a float type value.
~~~~

S2

~~~~
The radius within which to find mountains, measured in kilometers.
~~~~

#11 X

~~~~
The radius within which to find mountains, measured in kilometers. This is a float type value.
~~~~

#12 X

~~~~
The radius within which to find mountains, measured in kilometers. This is a float type value.
~~~~

X2

~~~~
The radius within which to find mountains, measured in kilometers. This is a float type value.
~~~~

#11 SX

~~~~
The radius within which to find mountains, measured in kilometers. This is a float type value.
~~~~

#12 SX

~~~~
The radius within which to find mountains, measured in kilometers. This is a float type value.
~~~~

SX2

~~~~
The radius within which to find mountains, measured in kilometers.
~~~~

#### locate_tallest_mountains `/function/parameters/properties/amount/description`

U

~~~~
The number of mountains to find, listed from tallest to smallest.
~~~~

#11 S

~~~~
Number of mountains to find, from tallest to smallest.
~~~~

#12 S

~~~~
The number of mountains to find, listed from tallest to smallest.
~~~~

S2

~~~~
The number of mountains to find, listed from tallest to smallest.
~~~~

#11 X

~~~~
The number of mountains to find, listed from tallest to smallest.
~~~~

#12 X

~~~~
The number of mountains to find, listed from tallest to smallest.
~~~~

X2

~~~~
The number of mountains to find, listed from tallest to smallest.
~~~~

#11 SX

~~~~
Number of mountains to find, from tallest to smallest.
~~~~

#12 SX

~~~~
The number of mountains to find, listed from tallest to smallest.
~~~~

SX2

~~~~
The number of mountains to find, listed from tallest to smallest.
~~~~

#### calculate_entropy_change `/function/parameters/properties/initial_temp/description`

U

~~~~
The initial temperature in Kelvin. This is a float type value.
~~~~

#11 S

~~~~
The initial temperature in Kelvin. This is a float type value.
~~~~

#12 S

~~~~
The initial temperature in Kelvin. This is a float type value.
~~~~

S2

~~~~
The initial temperature in Kelvin.
~~~~

#11 X

~~~~
The initial temperature in Kelvin. This is a float type value.
~~~~

#12 X

~~~~
The initial temperature in Kelvin. This is a float type value.
~~~~

X2

~~~~
The initial temperature in Kelvin. This is a float type value.
~~~~

#11 SX

~~~~
The initial temperature in Kelvin. This is a float type value.
~~~~

#12 SX

~~~~
The initial temperature in Kelvin. This is a float type value.
~~~~

SX2

~~~~
The initial temperature in Kelvin.
~~~~

#### calculate_entropy_change `/function/parameters/properties/final_temp/description`

U

~~~~
The final temperature in Kelvin. This is a float type value.
~~~~

#11 S

~~~~
The final temperature in Kelvin. This is a float type value.
~~~~

#12 S

~~~~
The final temperature in Kelvin. This is a float type value.
~~~~

S2

~~~~
The final temperature in Kelvin.
~~~~

#11 X

~~~~
The final temperature in Kelvin. This is a float type value.
~~~~

#12 X

~~~~
The final temperature in Kelvin. This is a float type value.
~~~~

X2

~~~~
The final temperature in Kelvin. This is a float type value.
~~~~

#11 SX

~~~~
The final temperature in Kelvin. This is a float type value.
~~~~

#12 SX

~~~~
The final temperature in Kelvin. This is a float type value.
~~~~

SX2

~~~~
The final temperature in Kelvin.
~~~~

#### calculate_entropy_change `/function/parameters/properties/heat_capacity/description`

U

~~~~
The heat capacity in J/K. This is a float type value.
~~~~

#11 S

~~~~
The heat capacity in J/K. This is a float type value.
~~~~

#12 S

~~~~
The heat capacity in J/K. This is a float type value.
~~~~

S2

~~~~
The heat capacity in J/K.
~~~~

#11 X

~~~~
The heat capacity in J/K. This is a float type value.
~~~~

#12 X

~~~~
The heat capacity in J/K. This is a float type value.
~~~~

X2

~~~~
The heat capacity in J/K. This is a float type value.
~~~~

#11 SX

~~~~
The heat capacity in J/K. This is a float type value.
~~~~

#12 SX

~~~~
The heat capacity in J/K. This is a float type value.
~~~~

SX2

~~~~
The heat capacity in J/K.
~~~~

### multiple_100

Exposed. Amendment no-op: `False`.

#### music_generator_generate_scale_progression `/function/description`

U

~~~~
Generate a music scale progression in a specific key with a given tempo and duration.
~~~~

#11 S

~~~~
Generate a music scale progression in a key, with a tempo and duration.
~~~~

#12 S

~~~~
Generate a music scale progression in a specific key with a given tempo and duration.
~~~~

S2

~~~~
Generate a music scale progression in a specific key with a given tempo and duration.
~~~~

#11 X

~~~~
Generate a music scale progression in a specific key with a given tempo and duration.
~~~~

#12 X

~~~~
Generate a music scale progression in a specific key with a given tempo and duration.
~~~~

X2

~~~~
Generate a music scale progression in a specific key with a given tempo and duration.
~~~~

#11 SX

~~~~
Generate a music scale progression in a key, with a tempo and duration.
~~~~

#12 SX

~~~~
Generate a music scale progression in a specific key with a given tempo and duration.
~~~~

SX2

~~~~
Generate a music scale progression in a specific key with a given tempo and duration.
~~~~

#### music_generator_generate_scale_progression `/function/parameters/properties/scale_type/description`

U

~~~~
The type of scale to generate. Defaults to 'major'.
~~~~

#11 S

~~~~
The type of scale to generate.
~~~~

#12 S

~~~~
The type of scale to generate.
~~~~

S2

~~~~
The type of scale to generate.
~~~~

#11 X

~~~~
The type of scale to generate. Defaults to 'major'.
~~~~

#12 X

~~~~
The type of scale to generate. Defaults to 'major'.
~~~~

X2

~~~~
The type of scale to generate. Defaults to 'major'.
~~~~

#11 SX

~~~~
The type of scale to generate.
~~~~

#12 SX

~~~~
The type of scale to generate.
~~~~

SX2

~~~~
The type of scale to generate.
~~~~

### simple_python_175

Exposed. Amendment no-op: `True`.

#### lawyer_get_experience `/function/parameters/properties/law_type/description`

U

~~~~
The type of law case. eg. Bankruptcy
~~~~

#11 S

~~~~
The type of law case.
~~~~

#12 S

~~~~
The type of law case. eg. Bankruptcy
~~~~

S2

~~~~
The type of law case. eg. Bankruptcy
~~~~

#11 X

~~~~
The type of law case. eg. Bankruptcy
~~~~

#12 X

~~~~
The type of law case. eg. Bankruptcy
~~~~

X2

~~~~
The type of law case. eg. Bankruptcy
~~~~

#11 SX

~~~~
The type of law case.
~~~~

#12 SX

~~~~
The type of law case. eg. Bankruptcy
~~~~

SX2

~~~~
The type of law case. eg. Bankruptcy
~~~~

### simple_python_34

Exposed. Amendment no-op: `True`.

#### travel_itinerary_generator `/function/description`

U

~~~~
Generate a travel itinerary based on specific destination, duration and daily budget, with preferred exploration type.
~~~~

#11 S

~~~~
Generate a travel itinerary from destination, duration, daily budget, and preferred exploration type.
~~~~

#12 S

~~~~
Generate a travel itinerary based on specific destination, duration and daily budget, with preferred exploration type.
~~~~

S2

~~~~
Generate a travel itinerary based on specific destination, duration and daily budget, with preferred exploration type.
~~~~

#11 X

~~~~
Generate a travel itinerary based on specific destination, duration and daily budget, with preferred exploration type.
~~~~

#12 X

~~~~
Generate a travel itinerary based on specific destination, duration and daily budget, with preferred exploration type.
~~~~

X2

~~~~
Generate a travel itinerary based on specific destination, duration and daily budget, with preferred exploration type.
~~~~

#11 SX

~~~~
Generate a travel itinerary from destination, duration, daily budget, and preferred exploration type.
~~~~

#12 SX

~~~~
Generate a travel itinerary based on specific destination, duration and daily budget, with preferred exploration type.
~~~~

SX2

~~~~
Generate a travel itinerary based on specific destination, duration and daily budget, with preferred exploration type.
~~~~

### irrelevance_59

Exposed. Amendment no-op: `True`.

No description differs across U, the systems-test edits, the #12 edits, and this amendment.

### irrelevance_50

Exposed. Amendment no-op: `False`.

#### convert_celsius_to_fahrenheit `/function/parameters/properties/celsius/description`

U

~~~~
The temperature in Celsius to be converted. This is a float type value.
~~~~

#11 S

~~~~
The temperature in Celsius to be converted. This is a float type value.
~~~~

#12 S

~~~~
The temperature in Celsius to be converted. This is a float type value.
~~~~

S2

~~~~
The temperature in Celsius to be converted.
~~~~

#11 X

~~~~
The temperature in Celsius to be converted. This is a float type value.
~~~~

#12 X

~~~~
The temperature in Celsius to be converted. This is a float type value.
~~~~

X2

~~~~
The temperature in Celsius to be converted. This is a float type value.
~~~~

#11 SX

~~~~
The temperature in Celsius to be converted. This is a float type value.
~~~~

#12 SX

~~~~
The temperature in Celsius to be converted. This is a float type value.
~~~~

SX2

~~~~
The temperature in Celsius to be converted.
~~~~
