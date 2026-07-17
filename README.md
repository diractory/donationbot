<div align="center">

<img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=28&pause=1000&color=F72585&center=true&vCenter=true&width=600&lines=Donation+Telegram+Bot;Feeding+Children+%26+Dogs%2C+One+Meal+at+a+Time;Built+with+Flask+%2B+MongoDB+%2B+Telegram+API" alt="Typing SVG" />

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)

</div>

---

## ❤️ About

A Flask + MongoDB Telegram bot that collects **one-time-meal donations** for
children and stray dogs — with QR-code payments, UTR + screenshot
verification, an admin approval channel, and built-in admin tools.

> Tap **Donate**, choose who you're feeding, pay via QR, and the team
> verifies + approves your donation right from Telegram. Simple, transparent,
> and fast. 🍛🐾

---

## ✨ Features

- 👋 Personalized `/start` greeting
- 🧒🐕 Choose **Children (₹30)** / **Dogs (₹20)** / **Both (₹50)** — donate more to feed extra
- 📝 Optional note, name-on-record, optional Instagram shout-out, email for proof
- ⏳ QR code that **auto-expires in 5 minutes**
- 🧾 UTR ID + payment screenshot verification
- 🔒 Donor details posted to the admin channel **hidden behind a spoiler**
- ✅❌ One-tap **Approve / Decline** for admins, with automatic donor notifications
- 📜 `/history` — donors can view their own donation history
- 📊 `/stats` and 📢 `/broadcast` — admin-only tools

---

## 🚀 Quick Start

1. Set your environment variables (`BOT_TOKEN`, `MONGO_URL`, `CHANNEL_ID`, `ADMIN_IDS`, `QR_IMAGE_URL`, `BASE_URL`, `WEBHOOK_SECRET`) — see `.env.example`
2. Deploy to Render (`Procfile` + `render.yaml` included)
3. Visit `/set_webhook` once, in your browser
4. Send `/start` to your bot 🎉

---

## 📂 Project Structure

```
app.py           Flask app + webhook endpoint
handlers.py      All conversation logic (the "brain")
db.py            MongoDB access layer
telegram_api.py  Thin wrapper around Telegram Bot API calls
keyboards.py     Inline keyboard builders
scheduler.py     Background timer to auto-delete the QR after 5 minutes
config.py        Reads all settings from environment variables
```

---

<div align="center">

```
┌──────────────────────────────────────────────┐
│                                                │
│   🧑‍💻  Made by Radhey                          │
│                                                │
│   💬  Telegram   : https://t.me/Youradhey      │
│   📢  Channel    : https://t.me/xivasudev      │
│                                                │
└──────────────────────────────────────────────┘
```

</div>

---

## ⭐ Support this project

If this bot helped you set up your donation drive, consider giving the repo
a star — it genuinely helps and takes two seconds! 🙏

<div align="center">

[![Star this repo](https://img.shields.io/badge/⭐_Star_this_repo-black?style=for-the-badge&logo=github)](../../stargazers)

</div>

---

<div align="center">
<sub>Built with ❤️ for a good cause — every meal counts.</sub>
</div>
<!-- hacktoberfest update 20260717121950147311 -->
<!-- run 1 @ 20260717122006248597 -->
<!-- run 2 @ 20260717122022250953 -->
<!-- run 3 @ 20260717122033973249 -->
<!-- run 4 @ 20260717122045878874 -->
<!-- run 5 @ 20260717122056861839 -->
<!-- run 6 @ 20260717122108155929 -->
<!-- run 7 @ 20260717122119003164 -->
<!-- run 8 @ 20260717122130278820 -->
<!-- run 9 @ 20260717122141416329 -->
<!-- run 10 @ 20260717122153089280 -->
<!-- run 11 @ 20260717122204030358 -->
<!-- run 12 @ 20260717122215167735 -->
<!-- run 13 @ 20260717122226596323 -->
<!-- run 14 @ 20260717122238391490 -->
<!-- run 15 @ 20260717122250195585 -->
