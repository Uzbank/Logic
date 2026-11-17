# Созлаш — фақат браузерда, Python шарт эмас (~30–40 дақиқа)

Ҳар бир қийматни олганингиз заҳоти уни шу ерга қўшинг:
**https://github.com/Uzbank/Logic/settings/secrets/actions → New repository secret** (Name ва Secret майдонлари).

## A. Claude калити → `ANTHROPIC_API_KEY`
1. https://console.anthropic.com/settings/billing → $10 баланс қўшинг.
2. https://console.anthropic.com/settings/keys → **Create Key** → нусха олинг.

## B. Telegram → `TELEGRAM_BOT_TOKEN`
1. Telegram'да **@BotFather** га `/newbot` ёзинг, ном беринг (масалан `logikmedia_helper_bot`).
2. У берган токенни нусха олинг.
3. Янги ботингизни очиб, **/start** босинг. (`TELEGRAM_CHAT_ID` ни E қадамда автоматик топамиз.)

## C. Google Cloud (YouTube рухсати)
1. https://console.cloud.google.com/projectcreate → Name: `LogikMedia` → **Create**.
2. https://console.cloud.google.com/apis/library/youtube.googleapis.com → **Enable**.
3. https://console.cloud.google.com/auth/overview → **Get started** → App name `LogikMedia Autopilot`, email'ингиз → **External** → **Create**.
4. https://console.cloud.google.com/auth/audience → **Publish app** → Confirm. (Акс ҳолда рухсат 7 кунда ўчади.)
5. https://console.cloud.google.com/auth/clients → **Create client** → Application type: **Web application** →
   "Authorized redirect URIs" → **Add URI** → `https://developers.google.com/oauthplayground` → **Create**.
6. Чиққан **Client ID** → `YT_CLIENT_ID`, **Client secret** → `YT_CLIENT_SECRET` қилиб GitHub'га қўшинг.

## D. YouTube токени → `YT_REFRESH_TOKEN`
1. https://developers.google.com/oauthplayground очинг.
2. Ўнг юқоридаги ⚙️ → **Use your own OAuth credentials** ни белгиланг → Client ID ва Client secret'ни киритинг.
3. Чапдаги "Input your own scopes" майдонига шуни ёзинг:
   `https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.upload`
   → **Authorize APIs**.
4. LogikMedia канали эгаси бўлган аккаунт билан киринг ва каналингизни танланг.
   "Google hasn't verified this app" чиқса → **Advanced** → **Go to LogikMedia Autopilot** → **Continue**.
5. **Exchange authorization code for tokens** → чиққан **Refresh token** ни нусха олиб, `YT_REFRESH_TOKEN` қилинг.

## E. Текшириш
1. https://github.com/Uzbank/Logic/actions/workflows/check.yml → **Run workflow**.
2. 1 дақиқадан кейин натижани очинг ("check" → "Run python pipeline.py check").
   Ундаги `>>> TELEGRAM_CHAT_ID ...: 123456789` рақамини `TELEGRAM_CHAT_ID` қилиб қўшинг.
3. Яна **Run workflow** → `ALL GOOD` чиқса ва Telegram'га тест хабар келса, тайёр.
4. Биринчи видео: https://github.com/Uzbank/Logic/actions/workflows/produce.yml → **Run workflow**.
