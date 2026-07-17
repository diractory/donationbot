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
<!-- run 16 @ 20260717122302114236 -->
<!-- run 17 @ 20260717122313883267 -->
<!-- run 18 @ 20260717122325727507 -->
<!-- run 19 @ 20260717122336940932 -->
<!-- run 20 @ 20260717122351989955 -->
<!-- run 21 @ 20260717122403030846 -->
<!-- run 22 @ 20260717122413817262 -->
<!-- run 23 @ 20260717122425165655 -->
<!-- run 24 @ 20260717122436455195 -->
<!-- run 25 @ 20260717122447962299 -->
<!-- run 26 @ 20260717122459977673 -->
<!-- run 27 @ 20260717122511231344 -->
<!-- run 28 @ 20260717122523167744 -->
<!-- run 29 @ 20260717122535012034 -->
<!-- run 30 @ 20260717122545562879 -->
<!-- run 31 @ 20260717122557076087 -->
<!-- run 32 @ 20260717122608256458 -->
<!-- run 33 @ 20260717122619155545 -->
<!-- run 34 @ 20260717122631512944 -->
<!-- run 35 @ 20260717122643360091 -->
<!-- run 36 @ 20260717122656046586 -->
<!-- run 37 @ 20260717122709456977 -->
<!-- run 38 @ 20260717122721715223 -->
<!-- run 39 @ 20260717122733081228 -->
<!-- run 40 @ 20260717122744143957 -->
<!-- run 41 @ 20260717122754993305 -->
<!-- run 42 @ 20260717122806385297 -->
<!-- run 43 @ 20260717122816946499 -->
<!-- run 44 @ 20260717122827910058 -->
<!-- run 45 @ 20260717122839094460 -->
<!-- run 46 @ 20260717122849930558 -->
<!-- run 47 @ 20260717122901125058 -->
<!-- run 48 @ 20260717122912147040 -->
<!-- run 49 @ 20260717122923170667 -->
<!-- run 50 @ 20260717122934218821 -->
<!-- run 51 @ 20260717122944896288 -->
<!-- run 52 @ 20260717122955574225 -->
<!-- run 53 @ 20260717123006695160 -->
<!-- run 54 @ 20260717123018135079 -->
<!-- run 55 @ 20260717123029798666 -->
<!-- run 56 @ 20260717123041853389 -->
<!-- run 57 @ 20260717123053246429 -->
<!-- run 58 @ 20260717123104377295 -->
<!-- run 59 @ 20260717123115170648 -->
<!-- run 60 @ 20260717123126195300 -->
<!-- run 61 @ 20260717123137442972 -->
<!-- run 62 @ 20260717123148671130 -->
<!-- run 63 @ 20260717123159670008 -->
<!-- run 64 @ 20260717123211457772 -->
<!-- run 65 @ 20260717123222553041 -->
<!-- run 66 @ 20260717123233564645 -->
<!-- run 67 @ 20260717123244666601 -->
<!-- run 68 @ 20260717123255622298 -->
<!-- run 69 @ 20260717123306624380 -->
<!-- run 70 @ 20260717123317781401 -->
<!-- run 71 @ 20260717123329109271 -->
<!-- run 72 @ 20260717123340951695 -->
<!-- run 73 @ 20260717123352166891 -->
<!-- run 74 @ 20260717123403613241 -->
<!-- run 75 @ 20260717123414696742 -->
<!-- run 76 @ 20260717123426537746 -->
<!-- run 77 @ 20260717123438495034 -->
<!-- run 78 @ 20260717123449797048 -->
<!-- run 79 @ 20260717123501170907 -->
<!-- run 80 @ 20260717123512767743 -->
<!-- run 81 @ 20260717123524507563 -->
<!-- run 82 @ 20260717123535975747 -->
