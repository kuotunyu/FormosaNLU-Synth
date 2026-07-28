# M11 real comparison evidence

Status: **complete**

| Utterance | Base intent | Adapted intent | Base latency | Adapted latency |
| --- | --- | --- | ---: | ---: |
| 播放周杰倫 | `INVALID` | `play_music` | 3744 ms | 2836 ms |
| 搜尋周杰倫的歌 | `INVALID` | `music_query` | 4011 ms | 2770 ms |
| 明天早上七點叫我起床 | `INVALID` | `alarm_set` | 3665 ms | 3467 ms |
| 台北明天會不會下雨 | `INVALID` | `weather_query` | 5035 ms | 3394 ms |
| 幫我寄信給小美說會晚到 | `INVALID` | `email_sendemail` | 4057 ms | 2457 ms |

Both paths use unconstrained generation. The base path receives the frozen zero-shot label catalog; the adapted path uses the frozen SFT prompt.
