# M3 Recipe Dry-run Samples

- Model: `qwen3.6:27b` (`a50eda8ed977ab48a124…`)
- Prompt versions: `hard_negative.v1`, `noise_codeswitch.v1`, `paraphrase.v1`, `slot_substitution.v1`
- Samples: 20（每個 recipe 5 筆）
- JSON-valid: 20/20
- Intent／slot／grounding contract valid: 16/20
- Measured wall time: 36.79 s

> 這是 M3 的人工 review 樣本，不是 M4 pilot，也不會用來調整 M4 固定門檻。

## `paraphrase`

| # | style | seed | intent | slots | output | contract |
|---:|---|---|---|---|---|---|
| 1 | `massive_like` | 5542 | `alarm_query` | [{"type":"date","value":"星期二的"},{"type":"event_name","value":"會議"}] | 查詢星期二會議設定的鬧鐘 | `F3_UNGROUNDED_SLOT` |
| 2 | `tw_colloquial` | 3152 | `alarm_remove` | [{"type":"time","value":"早上六點"}] | 把早上六點的鬧鐘取消 | `PASS` |
| 3 | `massive_like` | 5083 | `alarm_set` | [{"type":"time","value":"早上六點"}] | 設定早上六點的鬧鐘 | `PASS` |
| 4 | `tw_colloquial` | 3737 | `audio_volume_down` | [] | 把喇叭聲音調小一點 | `PASS` |
| 5 | `massive_like` | 4242 | `audio_volume_mute` | [] | 請保持安靜 | `PASS` |

## `slot_substitution`

| # | style | seed | intent | slots | output | contract |
|---:|---|---|---|---|---|---|
| 1 | `massive_like` | 5542 | `alarm_query` | [{"type":"date","value":"星期四"},{"type":"event_name","value":"會議"}] | 請幫我查詢為星期四會議設定的鬧鐘 | `PASS` |
| 2 | `tw_colloquial` | 3152 | `alarm_remove` | [{"type":"time","value":"早上四點"}] | 刪掉早上四點的鬧鐘 | `PASS` |
| 3 | `massive_like` | 5083 | `alarm_set` | [{"type":"time","value":"早上四點"}] | 設定一個早上四點的鬧鐘 | `PASS` |
| 4 | `tw_colloquial` | 2706 | `audio_volume_down` | [{"type":"change_amount","value":"到百分之十"}] | 把音量調低到百分之十 | `PASS` |
| 5 | `massive_like` | 607 | `audio_volume_mute` | [{"type":"time","value":"早上四點"}] | 設定早上四點靜音 | `PASS` |

## `noise_codeswitch`

| # | style | seed | intent | slots | output | contract |
|---:|---|---|---|---|---|---|
| 1 | `tw_colloquial` | 4980 | `audio_volume_other` | [] | 幫我把音量調高一點 | `PASS` |
| 2 | `tw_colloquial` | 3642 | `audio_volume_up` | [] | 我聽不到耶，你能不能再大聲點？ | `PASS` |
| 3 | `tw_colloquial` | 8930 | `calendar_query` | [{"type":"event_name","value":"會議"}] | 上次的會議耶，在什麼時候 | `PASS` |
| 4 | `tw_colloquial` | 7911 | `calendar_remove` | [{"type":"meal_type","value":"晚餐"},{"type":"person","value":"志豪"}] | 晚餐志豪我的啦 | `PASS` |
| 5 | `tw_colloquial` | 8411 | `calendar_set` | [] | 事件啦 | `PASS` |

## `hard_negative`

| # | style | seed | intent | slots | output | contract |
|---:|---|---|---|---|---|---|
| 1 | `massive_like` | ["5542","5083"] | `alarm_set` | [{"type":"date","value":"星期二的"},{"type":"event_name","value":"會議"}] | 設定星期二的會議鬧鐘 | `F2_SLOT_CONTRACT` |
| 2 | `tw_colloquial` | ["8930","8411"] | `calendar_set` | [{"type":"event_name","value":"會議"}] | 幫我把上次那個會議設成提醒 | `F2_SLOT_CONTRACT` |
| 3 | `massive_like` | ["10720","10814"] | `lists_createoradd` | [{"type":"list_name","value":"待辦"}] | 把購物加進我的待辦清單 | `PASS` |
| 4 | `tw_colloquial` | ["3456","88"] | `takeaway_order` | [{"type":"food_type","value":"漢堡"}] | 幫我訂漢堡 | `PASS` |
| 5 | `massive_like` | ["6374","1188"] | `play_music` | [{"type":"date","value":"今年"},{"type":"music_genre","value":"旋律"}] | 播放今年的旋律音樂 | `F2_SLOT_CONTRACT` |

## Review notes

- `slot_substitution` 的新 value 由程式從同 slot type 的 frozen train pool 選出，再交給 teacher 修語氣；label 不是由 teacher 猜。
- `noise_codeswitch` 按設計固定為 `tw_colloquial`；其他 recipe 同時覆蓋 `massive_like` 與 `tw_colloquial`。
- 原始結構化結果、tokens、每筆 provenance 與 reject reason 在 `reports/m3_recipe_samples.json`。
