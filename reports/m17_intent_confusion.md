# Per-intent movement is mostly seed variance

- Seeds: 42, 43, 44
- Intents analysed: 59
- Accuracy computed per seed, then summarised. Unparseable predictions
  count as wrong.

## The intents where one seed would mislead most

Ranked by how far the 20-shot baseline swings between seeds.

| Intent | n | real_only per seed | SD | real_syn_filtered per seed | SD |
|---|---:|---|---:|---|---:|
| `qa_factoid` | 141 | 18.4% / 70.2% / 85.8% | 35.3 | 69.5% / 71.6% / 81.6% | 6.4 |
| `calendar_set` | 209 | 80.4% / 70.8% / 39.2% | 21.5 | 73.7% / 78.9% / 76.6% | 2.6 |
| `general_quirky` | 169 | 62.7% / 41.4% / 24.9% | 19.0 | 30.2% / 45.0% / 37.9% | 7.4 |
| `email_querycontact` | 26 | 46.2% / 57.7% / 80.8% | 17.6 | 61.5% / 57.7% / 76.9% | 10.2 |
| `audio_volume_other` | 6 | 66.7% / 83.3% / 50.0% | 16.7 | 66.7% / 66.7% / 83.3% | 9.6 |

## Paired delta per seed for those intents

| Intent | per-seed Δ | mean Δ |
|---|---|---:|
| `qa_factoid` | +51.1 / +1.4 / -4.3 | +16.1 |
| `calendar_set` | -6.7 / +8.1 / +37.3 | +12.9 |
| `general_quirky` | -32.5 / +3.6 / +13.0 | -5.3 |
| `email_querycontact` | +15.4 / +0.0 / -3.8 | +3.8 |
| `audio_volume_other` | +0.0 / -16.7 / +33.3 | +5.6 |

## Where the confused rows go

### gold `general_quirky`

- `real_only`:
  - seed 42: general_quirky 106, general_greet 11, recommendation_events 6, weather_query 5, calendar_query 5, calendar_set 5
  - seed 43: general_quirky 70, qa_factoid 21, recommendation_events 7, news_query 7, recommendation_locations 7, general_greet 6
  - seed 44: qa_factoid 45, general_quirky 42, recommendation_movies 13, general_greet 10, lists_createoradd 5, recommendation_events 5
- `real_syn_filtered`:
  - seed 42: general_quirky 51, qa_factoid 27, recommendation_events 10, general_greet 8, calendar_set 8, weather_query 6
  - seed 43: general_quirky 76, qa_factoid 18, general_greet 10, recommendation_movies 8, calendar_query 5, calendar_set 5
  - seed 44: general_quirky 64, qa_factoid 29, weather_query 6, recommendation_movies 6, qa_definition 6, recommendation_events 6

### gold `qa_factoid`

- `real_only`:
  - seed 42: general_quirky 98, qa_factoid 26, transport_query 3, weather_query 3, recommendation_locations 2, qa_definition 2
  - seed 43: qa_factoid 99, general_quirky 18, recommendation_locations 6, transport_query 4, email_querycontact 3, qa_definition 3
  - seed 44: qa_factoid 121, recommendation_locations 6, general_quirky 2, email_querycontact 2, qa_definition 2, weather_query 2
- `real_syn_filtered`:
  - seed 42: qa_factoid 98, qa_definition 9, general_quirky 7, datetime_query 4, weather_query 4, news_query 3
  - seed 43: qa_factoid 101, general_quirky 12, qa_maths 5, qa_definition 5, recommendation_locations 4, email_querycontact 3
  - seed 44: qa_factoid 115, qa_definition 6, general_quirky 4, email_querycontact 3, transport_query 3, recommendation_locations 2

Per-intent figures from one seed can differ from the three-seed mean by tens of points. Accuracy is computed per seed and then summarised; unparseable predictions count as wrong.
