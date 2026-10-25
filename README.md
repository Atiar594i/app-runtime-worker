# 🤖 Telegram Account & Session Receiver Bot

একটি আধুনিক, নিরাপদ এবং স্কেলেবল **Telegram Session & OTP Receiver Bot** (হুবহু ভিডিও অনুযায়ী নির্মিত)। এই বটের মাধ্যমে ব্যবহারকারীরা টেলিগ্রাম নম্বর ও ওটিপি কোড সাবমিট করে তাদের টেলিগ্রাম অ্যাকাউন্ট বিক্রয়/জমা দিতে পারে এবং স্বয়ংক্রিয়ভাবে ব্যালেন্স উপার্জন করে উইথড্র করতে পারে। অ্যাডমিন প্যানেল থেকে সমস্ত রেট, ক্যাপাসিটি, চ্যানেল, প্ল্যাটফর্ম এবং টেকনিক্যাল সেটিংস লাইভ পরিবর্তন করা যায়।

---

## 🌟 প্রধান প্রধান ফিচারসমূহ (Key Features)

### ১. সাধারণ ব্যবহারকারী ফিচার (User Features)
- **`/start`**: ইউজারকে নামসহ স্বাগতম জানানো এবং ব্যবহারের নিয়ম ও উদাহরণ প্রদর্শন। (Force Join চ্যানেল চালু থাকলে বাধ্যতামূলক চ্যানেল জয়েন যাচাই)।
- **`/cancel`**: চলমান যেকোনো লগইন বা ইনপুট প্রসেস বাতিল করা।
- **`/capacity`**: কান্ট্রি কোড, স্ট্যাটাস, কনফার্মেশন টাইম (যেমন: 600s) এবং ক্যাটাগরি ভিত্তিক প্রাইস (Free, Spam, New Acc) এর তালিকা।
- **`/balance`**: ইউজারের তথ্য (Name, User ID, Username, Balance, Accounts Sold) সহ:
  - **💳 Withdraw Balance**: ব্যালেন্স উত্তোলনের রিকোয়েস্ট তৈরি (ন্যূনতম উইথড্র চেক, মেথড ও ওয়ালেট ইনপুট)।
  - **📜 Withdraw History**: পূর্বের উইথড্র রিকোয়েস্ট ও স্ট্যাটাস দেখা।
- **`/help`**: সাপোর্ট এডমিন ও আপডেট চ্যানেলের ডিরেক্ট লিংক।
- **স্বয়ংক্রিয় লগইন ও ওটিপি রিসিভার**:
  - কান্ট্রি কোডসহ নম্বর পাঠালে স্বয়ংক্রিয়ভাবে Telethon ক্লায়েন্ট সংযোগ এবং ওটিপি কোড পাঠানো।
  - টাইমার কাউন্টডাউন (কনফার্মেশন টাইমআউট)।
  - 2FA (Two-Step Verification) হ্যান্ডলিং।
  - `@SpamBot` স্বয়ংক্রিয় চেক করে অ্যাকাউন্ট ক্যাটাগরি ডিটেকশন (Free / Clean, Spam, Permanent Spam, New Register)।
  - নির্ধারিত ক্যাটাগরি অনুযায়ী ইউজারের ব্যালেন্সে ইনস্ট্যান্ট টাকা/ডলার যোগ এবং Stats চ্যানেলে নোটিফিকেশন।

---

### ২. পূর্ণাঙ্গ অ্যাডমিন প্যানেল (`/admin` Command)
- 🌍 **Country Settings**:
  - নতুন দেশ (Country) যুক্ত করা (Name, Code, Capacity, Main Price, Spam Price, New Acc Price, Confirm Time)।
  - দেশের স্ট্যাটাস অন/অফ (Active/Inactive টগল)।
  - **Premium Only** টগল (শুধুমাত্র প্রিমিয়াম ইউজারদের অনুমতি)।
  - **Accept Spam** টগল (স্প্যাম অ্যাকাউন্ট গ্রহণ/বর্জন)।
  - **Login Email** টগল।
  - প্রাইস ও ক্যাপাসিটি এডিট এবং কান্ট্রি ডিলিট।
- 📢 **Channel Management**:
  - **Payment Channel**: সফল উইথড্র নোটিফিকেশন ও প্রুফ পাঠানোর চ্যানেল।
  - **Stats Channel**: নতুন অ্যাকাউন্ট কনফার্মেশনের লাইভ রিপোর্ট চ্যানেল।
  - **Join Lock (Force Join)**: বট ব্যবহার করার পূর্বে জয়েন বাধ্যতামূলক করার চ্যানেল।
  - **Error Report Channel**: সিস্টেমে কোনো ত্রুটি দেখা দিলে স্বয়ংক্রিয় নোটিফিকেশন চ্যানেল।
- 💰 **Finance**:
  - ইউজারের ব্যালেন্স যোগ (Add Balance) বা বিয়োগ (Deduct Balance)।
  - ইউজার ব্যান (Ban) ও আনব্যান (Unban)।
  - সবার ব্যালেন্স একসাথে রিসেট (Reset All Balances)।
  - সমস্ত ইউজার ডেটা এক্সেল (`.xlsx`) ফাইলে এক্সপোর্ট।
- 💳 **Withdrawals**:
  - পেন্ডিং উইথড্র তালিকা দেখা এবং এক ক্লিকে **Approve & Pay** অথবা **Reject (Auto Refund)** করা।
  - W-ID অথবা User ID দিয়ে উইথড্র স্ট্যাটাস অনুসন্ধান।
  - সম্পূর্ণ উইথড্র ডেটা এক্সেল ফাইলে এক্সপোর্ট।
  - নির্দিষ্ট তারিখ অনুযায়ী (Date Filter) উইথড্র এক্সেল ডাউনলোড।
- 🛠 **User Tools**:
  - দেশ অনুযায়ী ইউজার ও অ্যাকাউন্টের পরিসংখ্যান দেখা।
  - ফোন নম্বর দিয়ে ইউজার ও অ্যাকাউন্টের ইতিহাস বের করা।
  - নষ্ট বা অকার্যকর নম্বর ও সেশন মুছে ফেলা (Delete Bad Numbers/Sessions)।
- 📁 **Accounts Manager**:
  - Total Confirmed, Pending এবং Downloaded পরিসংখ্যান।
  - বিভিন্ন ক্যাটাগরিতে সেশন ফাইল (`.session`) ZIP আকারে ডাউনলোড (All Confirmed, Free, Spam, New Acc)।
  - অ্যাকাউন্ট রিপোর্টের পূর্ণাঙ্গ এক্সেল শিট ডাউনলোড।
- 📊 **Daily Summary**:
  - আজকের মোট ইউজার, নতুন ইউজার, অ্যাকাউন্ট হিট সংখ্যা, মোট ফাইন্যান্স ও উইথড্রল হিসেব।
  - সার্ভারের রিয়েলটাইম হেলথ স্ট্যাটাস (CPU Usage %, RAM Usage %, Disk Space)।
- ⚙️ **Configuration**:
  - Maintenance Mode (অন/অফ টগল)।
  - Withdraw System (অন/অফ টগল)।
  - Receive System (অন/অফ টগল)।
  - Minimum Withdrawal Amount (Min WD) সেট করা।
  - Default 2FA Pass সেট করা (লগইন হওয়া অ্যাকাউন্টে স্বয়ংক্রিয় পাসওয়ার্ড সিকিউরিটি)।
  - নতুন অ্যাডমিন যোগ ও রিমুভ করা।
  - **Full System Backup**: ডাটাবেজ ও সমস্ত সেশন ফাইল এক ক্লিকে জিপ ব্যাকআপ ডাউনলোড।

---

### ৩. ব্যাকএন্ড ও টেকনিক্যাল সেটিংস (Technical Presets)
- ⚙️ **API Configuration**:
  - অ্যাডমিন প্যানেল থেকেই **App ID**, **App Hash**, **System Lang Code**, এবং **App Version** ডায়নামিকালি পরিবর্তন করার সুবিধা।
- 📱 **Platform Selection**:
  - **TD-direct**: Telegram Desktop Direct API (Windows 11 x64)
  - **Android**: Official Telegram for Android (Samsung Galaxy S24 Ultra)
  - **Bot Android**: Custom Preset (Google Pixel 8 Pro)
- 🌐 **Proxy Settings**:
  - HTTP এবং SOCKS5 প্রক্সি কনফিগারেশন।
  - প্রক্সি অন/অফ টগল।
  - **Test Ping**: টেলিগ্রাম ডাটা সেন্টারের সাথে প্রক্সির কানেকশন ও লেটেন্সি (ms) টেস্ট।
  - **Change ISO**: প্রক্সি জিও-রাউটিং এর জন্য কান্ট্রি কোড পরিবর্তন।

---

## 📁 প্রজেক্ট স্ট্রাকচার (Project Structure)

```text
bot/
├── main.py                     # বট এর মূল রানার ও ইভেন্ট ডিসপ্যাচার
├── config.py                   # কনফিগারেশন, পাথ ও ডিফল্ট এনভায়রনমেন্ট
├── database.py                 # SQLite অ্যাসিঙ্ক ডাটাবেজ মডেল ও কুয়েরি
├── session_manager.py          # Telethon সেশন ও ওটিপি ভেরিফিকেশন ইঞ্জিন
├── requirements.txt            # প্রয়োজনীয় পাইথন লাইব্রেরি
├── .env.example                # এনভায়রনমেন্ট ভ্যারিয়েবল টেমপ্লেট
│
├── handlers/                   # বট মেসেজ ও কলব্যাক হ্যান্ডলারসমূহ
│   ├── __init__.py
│   ├── user_handlers.py        # ইউজার কমান্ড, ব্যালেন্স, উইথড্র ও ওটিপি ফ্লো
│   ├── admin_handlers.py       # অ্যাডমিন মেইন মেনু ও ইনপুট FSM
│   ├── country_handlers.py     # কান্ট্রি সেটিংস, টগল ও প্রাইসিং
│   ├── finance_handlers.py     # ব্যালেন্স অ্যাড/মাইনাস, ব্যান ও এক্সেল এক্সপোর্ট
│   ├── withdraw_handlers.py    # উইথড্র পেন্ডিং এপ্রুভ/রিজেক্ট ও ফিল্টারিং
│   ├── account_handlers.py     # সেশন জিপ ডাউনলোড ও অ্যাকাউন্ট রিপোর্ট
│   └── tech_handlers.py        # API কনফিগ, প্ল্যাটফর্ম, প্রক্সি ও চ্যানেল
│
├── utils/                      # হেল্পার ও ইউটিলিটি মডিউল
│   ├── __init__.py
│   ├── helpers.py              # ফোন নরমালাইজার, ফোর্স জয়েন, পিং ও ব্যাকআপ
│   ├── excel_export.py         # openpyxl এক্সেল ফাইল জেনারেটর
│   └── platform_presets.py     # TD-direct ও Android ডিভাইস প্যারামিটার
│
├── sessions/                   # টেলিগ্রাম সেশন স্টোরেজ
│   ├── temp/                   # ওটিপি ভেরিফিকেশনের সাময়িক সেশন
│   └── confirmed/              # নিশ্চিত হওয়া সংরক্ষিত সেশন
│       ├── free/               # ক্লিন / রেস্ট্রিকশন মুক্ত অ্যাকাউন্ট
│       ├── spam/               # স্প্যামবট সীমিত অ্যাকাউন্ট
│       └── new_acc/            # নতুন রেজিস্টার্ড অ্যাকাউন্ট
└── exports/                    # সাময়িক এক্সেল ও জিপ ব্যাকআপ ফোল্ডার
```

---

## 🚀 সেটআপ ও ইনস্টলেশন নির্দেশিকা (Installation Guide)

### ১. ডিপেন্ডেন্সি ইনস্টল করুন
আপনার টার্মিনালে নিচের কমান্ডটি রান করুন:
```bash
pip install -r requirements.txt
```

### ২. কনফিগারেশন (.env) তৈরি করুন
প্রজেক্ট ফোল্ডারে `.env` নামে একটি ফাইল তৈরি করুন এবং `.env.example` অনুযায়ী আপনার টোকেন দিন:
```env
# BotFather থেকে পাওয়া বট টোকেন
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRstuVWXyz123456789

# আপনার টেলিগ্রাম আইডি (অ্যাডমিন আইডি)
ADMIN_IDS=123456789

# টেলিগ্রাম API আইডি ও হ্যাশ (https://my.telegram.org থেকে পাওয়া)
API_ID=2040
API_HASH=b18441a1ff607e10a989891a5462e627
```

### ৩. বট রান করুন
```bash
python main.py
```

---

## 🔒 লিনাক্স সার্ভারে ২৪/৭ রান করার নিয়ম (Linux VPS Systemd Service)

সার্ভারে ব্যাকগ্রাউন্ডে সবসময় চালু রাখার জন্য systemd সার্ভিস ব্যবহার করুন:

১. সার্ভিস ফাইল তৈরি করুন:
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

২. নিচের কোডটি পেস্ট করুন:
```ini
[Unit]
Description=Telegram Account Receiver Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bot
ExecStart=/usr/bin/python3 /root/bot/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

৩. সার্ভিস চালু ও অটো-স্টার্ট এনেবল করুন:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

---

## 🛡 সিকিউরিটি ও বেস্ট প্র্যাকটিস (Security & Best Practices)

1. **2FA Pass সুরক্ষা**: অ্যাডমিন প্যানেল থেকে `Default 2FA Pass` সেট করে রাখলে নতুন যুক্ত হওয়া অ্যাকাউন্টে স্বয়ংক্রিয়ভাবে 2FA এনাবল হয়ে যায়, ফলে ইউজার পরে অ্যাকাউন্ট ফিরিয়ে নিতে পারে না।
2. **Force Join**: চ্যানেল লক যুক্ত রাখলে ব্যবহারকারীকে অবশ্যই আপনার অফিশিয়াল চ্যানেলে যুক্ত থাকতে হবে।
3. **প্রক্সি ব্যবহার**: প্রচুর অ্যাকাউন্ট হ্যান্ডেল করার সময় টেলিগ্রামের IP Flood লিমিট এড়াতে Proxy Settings থেকে SOCKS5/HTTP প্রক্সি ব্যবহার করার সুবিধা রয়েছে।
