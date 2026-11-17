# LogikMedia Autopilot — ўзи тема топиб, видео қилиб, YouTube'га қўядиган агентлар

## Нима қилади

Ҳафтасига 2 марта (душанба ва пайшанба, Тошкент вақти 19:00) GitHub серверида ўзи ишга тушади:

1. **Тадқиқотчи агент (Claude + веб қидирув)** — охирги 14 кундаги AI янгиликларини ва YouTube'да нишада энг кўп кўрилаётган видеоларни ўрганиб, 5 та тема таклиф қилади.
2. **Сценарист агент (Claude)** — энг яхши темани танлаб, ~8 дақиқалик инглизча сценарий, сарлавҳа, тавсиф, теглар ва манбаларни ёзади. Олдинги темаларни такрорламайди.
3. **Овоз** — бепул Microsoft неврал овози (edge-tts) ёки ElevenLabs (калит берилса, сифатлироқ).
4. **Монтаж** — LogikMedia брендидаги (тўқ кўк + циан) слайдлар, секин зум, субтитр, логотип, хоҳласангиз фон мусиқаси.
5. **Thumbnail** — автоматик.
6. **YouTube'га юклаш** — YouTube Data API орқали, **private** ҳолатда.
7. **1 дақиқалик текширув (Telegram)** — телефонингизга видео линки ва ✅ / ❌ тугмалари келади. ✅ боссангиз, сешанба/жума 9:00 (АҚШ шарқий вақти) да ўзи чиқади.

Сиздан талаб қилинадиган вақт: бир марта ~1 соат созлаш, кейин ҳафтасига 2 марта 1–5 дақиқа (Telegram'да кўриб, тугма босиш).

## Формат: AI Battle (асосий)

Ҳар видеода AI'лар битта кичик бизнес учун 3 та ҳақиқий топшириқда беллашади. Экранда уларнинг **ҳақиқий жавоблари**, ўлчанган вақт, сўзлар сони ва нархи, яширин ҳакамнинг баллари, жадвал ва ғолиб кўрсатилади. Ҳеч бир жавоб ўйлаб топилмайди.
- Фақат `ANTHROPIC_API_KEY` бўлса: Claude Haiku / Sonnet / Opus ("арзон ва қиммат") ёки "промпт баттл".
- `GEMINI_API_KEY` (aistudio.google.com/apikey, бепул) ва/ёки `OPENAI_API_KEY` қўшилса: Claude vs Gemini vs ChatGPT.
- Эски слайд формати: `config.toml` → `[content] format = "explainer"`.

## Ҳалол огоҳлантиришлар (муҳим)

- **YouTube монетизацияси.** YouTube "inauthentic / mass-produced content" (оммавий, такрорий контент) сиёсати бўйича шаблон асосида кўп чиқарилган паст сифатли видеоларни монетизациядан рад этади. Шунинг учун: ҳафтасига 2 тадан ошириб юборманг, ҳар видео реал манбаларга таянади, ва **Telegram тасдиғини ўчирманг** (`review.mode = "opt_in"`). Энг яхши натижа учун вақти-вақти билан ўзингиз экран ёзувли реал тест видеосини ҳам қўшинг — каналнинг асосий режаси шунга қурилган.
- **API аудит.** Янги Google Cloud лойиҳаси орқали API билан юкланган видеолар Google аудитдан ўтмагунча **фақат private** бўлиб қолади (бу YouTube қоидаси). Аудит бепул, "YouTube API Services Audit and Quota Extension Form" орқали сўралади, бир неча ҳафта олиши мумкин. Ўшангача: видео private юкланади, сиз Studio'да "Public" ни ўзингиз босасиз (1 клик).
- **OAuth "Testing" режими.** Google Cloud'даги OAuth consent screen "Testing" ҳолатида қолса, токен 7 кунда ўчади. Уни **"In production"** га ўтказинг (ўзингиз учун текширув шарт эмас, огоҳлантириш ойнаси чиқади, "Continue" босилади).
- **edge-tts** — норасмий бепул сервис, баъзан ишламай қолиши мумкин. Барқарорлик учун ElevenLabs калитини қўшиш тавсия этилади.
- Ўзбекистон ҳозирча YPP мамлакатлари рўйхатида йўқ — режадагидек аввал аффилиат ва спонсорлардан даромад.

## Сизнинг қўлингизда керак бўладиган нарсалар (калитлар)

| # | Нима | Қаердан | Нархи |
|---|---|---|---|
| 1 | GitHub аккаунти + **private** репозиторий | github.com | бепул |
| 2 | `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | ~$0.5–1 бир видеога |
| 3 | Google Cloud лойиҳа + **YouTube Data API v3** ёқилган + OAuth Client (Desktop app) → `client_secret.json` | console.cloud.google.com | бепул |
| 4 | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | `auth_youtube.py` ни бир марта ишлатиб оласиз | бепул |
| 5 | `TELEGRAM_BOT_TOKEN` | Telegram'да @BotFather → /newbot | бепул |
| 6 | `TELEGRAM_CHAT_ID` | ботга "hi" ёзинг, кейин `https://api.telegram.org/bot<TOKEN>/getUpdates` очинг, `"chat":{"id":...}` рақами | бепул |
| 7 | (ихтиёрий) `ELEVENLABS_API_KEY` | elevenlabs.io | $5–22/ой |
| 8 | YouTube каналда телефон тасдиқлаш (custom thumbnail учун) | youtube.com/verify | бепул |

## Созлаш қадамлари (~1 соат, бир марта)

> Энг осон йўл (фақат браузер, Python'сиз): **[SETUP.md](SETUP.md)**. Қуйидагиси муқобил йўл.

1. GitHub'да янги **private** репозиторий очинг (масалан `logikmedia-autopilot`) ва шу папкадаги ҳамма файлларни юкланг (`.github` папкаси билан бирга).
2. Google Cloud: янги лойиҳа → "APIs & Services" → **YouTube Data API v3** ни Enable қилинг → "OAuth consent screen" (External, ўзингизни test user қилиб қўшинг, кейин **Publish app → In production**) → "Credentials" → Create OAuth client ID → **Desktop app** → JSON'ни `client_secret.json` деб юклаб олинг.
3. Ўз компьютерингизда (Python 3.10+):
   ```
   pip install google-auth-oauthlib
   python auth_youtube.py client_secret.json
   ```
   Браузерда LogikMedia канали эгаси бўлган Google аккаунт билан киринг. Экранга 3 та қиймат чиқади.
4. GitHub репо → Settings → Secrets and variables → Actions → **New repository secret**: юқоридаги жадвалдаги ҳар бир калитни шу номлар билан қўшинг.
5. Синов: репо → **Actions** → "Produce video" → **Run workflow**. 10–20 дақиқада Telegram'га видео келади.
6. Тайёр. Кейин ҳаммаси жадвал бўйича ўзи ишлайди.

## Созламалар (`config.toml`)

- `schedule.days`, `schedule.hour` — қайси кунлари чиқиши.
- `review.mode` — `opt_in` (тавсия: ✅ босмагунча чиқмайди), `opt_out` (ўзи чиқади, ❌ билан тўхтатасиз), `off` (тавсия этилмайди).
- `channel.seed_keywords`, `channel.niche` — мавзулар йўналиши.
- `voice.edge_voice` — овоз (масалан `en-US-GuyNeural`, `en-US-AriaNeural`).
- `assets/music.mp3` қўйсангиз, фон мусиқаси сифатида паст овозда қўшилади (YouTube Audio Library'дан лицензияли мусиқа олинг).

## Локал синов (калитсиз)

```
pip install -r requirements.txt   # + ffmpeg ўрнатилган бўлсин
python pipeline.py produce --dry-run      # намуна сценарий билан видео ясайди, юкламайди
python pipeline.py produce --no-upload    # реал тема ва сценарий, лекин юкламайди
```

## Харажат (тахминан, ойига 8 видео)

- Claude API: ~$4–8
- GitHub Actions: бепул (private репода ойига 2000 дақиқа, бу ~900 ишлатади)
- YouTube API квотаси: бепул (кунига 10 000 бирлик, битта видео ~2 000)
- ElevenLabs (ихтиёрий): $5–22

## Файллар

- `pipeline.py` — асосий дастур (`produce`, `review`)
- `lm/writer.py` — тадқиқотчи ва сценарист агентлар (Claude)
- `lm/voice.py` — овоз, `lm/visuals.py` — слайд ва thumbnail, `lm/assemble.py` — монтаж
- `lm/youtube.py` — юклаш ва жадвал, `lm/telegram.py` — ✅/❌ тасдиқ
- `.github/workflows/` — жадвал (душ/пай видео, ҳар соат тасдиқларни текшириш)
- `data/topics_used.json` — ишлатилган темалар (такрорланмаслик учун)
