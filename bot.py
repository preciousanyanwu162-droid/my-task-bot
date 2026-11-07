import telebot
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# Safe token loading
token_env = os.environ.get("BOT_TOKEN")
if not token_env:
    print("ERROR: BOT_TOKEN is missing!")
    exit(1)
TOKEN = token_env.strip()

VERIFY_LINK = "https://qkzpkdm.com/cl/74eeb46afeff0fcd"
TIMEBUCKS_REF_LINK = "https://timebucks.com/?refID=229160569"
PEERPURSE_CODE = "360366"

ADMIN_ID = 7109418504
user_data = {}
pending_withdraw = {}
DATA_FILE = "data.json"
WITHDRAW_MIN = 3500

main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.row(KeyboardButton("💳 Balance"), KeyboardButton("🏧 Withdraw"))
main_keyboard.row(KeyboardButton("🔗 Referral"), KeyboardButton("🎁 TimeBucks"))
main_keyboard.row(KeyboardButton("🎁 PeerPurse"))

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        user_data = json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(user_data, f)

bot = telebot.TeleBot(TOKEN)

def is_verified(uid):
    return user_data.get(uid, {}).get("verified", False)

# ---------- START (REFERRAL) ----------
# This MUST be placed above the normal start command
@bot.message_handler(commands=['start'], func=lambda msg: msg.text and msg.text.startswith('/start ref_'))
def start_ref(msg):
    ref_id = msg.text.split()[1].replace('ref_', '')
    uid = str(msg.from_user.id)
    if uid not in user_data:
        user_data[uid] = {"balance": 0, "referrer": ref_id, "ref_credited": False, "verified": False}
    else:
        user_data[uid]["referrer"] = ref_id
    save_data()
    start(msg)

# ---------- START (NORMAL) ----------
@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.from_user.id)
    if uid not in user_data:
        user_data[uid] = {
            "balance": 0,
            "referrer": None,
            "ref_credited": False,
            "verified": False
        }
        save_data()
    if not is_verified(uid):
        send_verification_prompt(msg.chat.id, uid)
        return
    bot.send_message(msg.chat.id,
        "✅ Welcome back! Use the buttons below.\n"
        "💳 Balance – check balance\n"
        "🏧 Withdraw – cash out at ₦" + str(WITHDRAW_MIN) + "\n"
        "🔗 Referral – get your link\n"
        "🎁 TimeBucks – earn bonus\n"
        "🎁 PeerPurse – earn bonus",
        reply_markup=main_keyboard)

# ---------- VERIFICATION PROMPT ----------
def send_verification_prompt(chat_id, uid):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📱 Tap to Verify / Subscribe", url=VERIFY_LINK))
    markup.add(InlineKeyboardButton("✅ I have completed the subscription", callback_data="verify_done"))
    text = (
        "⚠️ **VERIFICATION REQUIRED** ⚠️\n\n"
        "You must complete a simple subscription task before you can use this bot.\n"
        "1. Tap the button below to complete the subscription.\n"
        "2. Return here and tap **✅ I have completed the subscription**.\n\n"
        "💰 You will receive **₦1,000** in your balance immediately after verification!\n"
        "🚫 You cannot use any feature until this is done."
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "verify_done")
def verify_done(call):
    uid = str(call.from_user.id)
    if uid not in user_data:
        user_data[uid] = {"balance":0,"referrer":None,"ref_credited":False,"verified":False}
    if user_data[uid].get("verified", False):
        bot.answer_callback_query(call.id, "You are already verified!")
        return
    user_data[uid]["verified"] = True
    user_data[uid]["balance"] += 1000
    save_data()
    bot.answer_callback_query(call.id, "Verification complete! ₦1,000 credited.")
    bot.edit_message_text(
        "✅ **Verification successful!**\n\n"
        "₦1,000 has been added to your balance.\n"
        "You can now use all features. Tap /start to see your menu.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )
    ref_id = user_data[uid].get("referrer")
    if ref_id and not user_data[uid].get("ref_credited", False):
        if ref_id in user_data and user_data[ref_id].get("verified", False):
            user_data[ref_id]["balance"] += 100
            user_data[uid]["ref_credited"] = True
            save_data()
            try:
                bot.send_message(int(ref_id), "🎉 Your referral has been verified! ₦100 added to your balance.")
            except:
                pass

# ---------- UNIVERSAL TEXT HANDLER ----------
BUTTON_MAP = {
    "💳 Balance": "/balance",
    "🏧 Withdraw": "/withdraw",
    "🔗 Referral": "/referral",
    "🎁 TimeBucks": "/jointask1",
    "🎁 PeerPurse": "/jointask2"
}

@bot.message_handler(func=lambda msg: True, content_types=['text'])
def universal_text_handler(msg):
    uid = str(msg.from_user.id)
    text = msg.text.strip()

    if not is_verified(uid):
        send_verification_prompt(msg.chat.id, uid)
        return

    if text in BUTTON_MAP:
        cmd = BUTTON_MAP[text]
        msg.text = cmd
        if cmd == "/balance":
            balance(msg)
        elif cmd == "/withdraw":
            withdraw(msg)
        elif cmd == "/referral":
            referral(msg)
        elif cmd == "/jointask1":
            jointask1(msg)
        elif cmd == "/jointask2":
            jointask2(msg)
        return

    if pending_withdraw.get(uid, False):
        collect_bank_details(msg)
        return

    bot.send_message(msg.chat.id, "🤔 I didn't understand that. Please use the buttons or commands.", reply_markup=main_keyboard)

# ---------- BALANCE ----------
@bot.message_handler(commands=['balance'])
def balance(msg):
    uid = str(msg.from_user.id)
    if not is_verified(uid):
        send_verification_prompt(msg.chat.id, uid)
        return
    bal = user_data.get(uid, {}).get("balance", 0)
    bot.send_message(msg.chat.id, f"💰 Your balance: ₦{bal}", reply_markup=main_keyboard)

# ---------- WITHDRAWAL ----------
@bot.message_handler(commands=['withdraw'])
def withdraw(msg):
    uid = str(msg.from_user.id)
    if not is_verified(uid):
        send_verification_prompt(msg.chat.id, uid)
        return
    bal = user_data.get(uid, {}).get("balance", 0)
    if bal < WITHDRAW_MIN:
        bot.send_message(msg.chat.id, f"🏧 Minimum withdrawal is ₦{WITHDRAW_MIN}. Your balance: ₦{bal}", reply_markup=main_keyboard)
        return
    bot.send_message(msg.chat.id, "📝 To withdraw, please send your **bank name** and **account number**. We process payouts every Friday.", reply_markup=main_keyboard)
    pending_withdraw[uid] = True

def collect_bank_details(msg):
    uid = str(msg.from_user.id)
    bot.forward_message(ADMIN_ID, msg.chat.id, msg.message_id)
    bot.send_message(msg.chat.id, "✅ Your details have been sent. We will process your withdrawal soon.", reply_markup=main_keyboard)
    pending_withdraw[uid] = False

# ---------- REFERRAL ----------
@bot.message_handler(commands=['referral'])
def referral(msg):
    uid = str(msg.from_user.id)
    if not is_verified(uid):
        send_verification_prompt(msg.chat.id, uid)
        return
    bot_name = bot.get_me().username
    bot.send_message(msg.chat.id, f"🔗 Your referral link:\nhttps://t.me/{bot_name}?start=ref_{msg.from_user.id}\n\nShare it. When someone joins and completes verification, you get ₦100.", reply_markup=main_keyboard)

# ---------- EXTRA TASK 1 (TIMEBUCKS) ----------
@bot.message_handler(commands=['jointask1'])
def jointask1(msg):
    uid = str(msg.from_user.id)
    if not is_verified(uid):
        send_verification_prompt(msg.chat.id, uid)
        return
    if uid not in user_data:
        user_data[uid] = {"balance": 0, "referrer": None, "ref_credited": False, "verified": False}
    bot.send_message(msg.chat.id,
        f"📌 **Task: Sign up on TimeBucks**\n\n"
        f"1. Click this link and sign up **using only your Google account**:\n{TIMEBUCKS_REF_LINK}\n"
        f"2. After successful registration, perform 1 task and press the button below to claim ₦100.\n\n"
        f"⚠️ You must use Google sign‑up and perform at least one task, otherwise the reward won't be credited.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("I've signed up ✅", callback_data=f"timebucks_{uid}"))
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('timebucks_'))
def timebucks_done(call):
    uid = str(call.from_user.id)
    if not is_verified(uid):
        bot.answer_callback_query(call.id, "Please complete verification first.")
        return
    if uid not in user_data:
        user_data[uid] = {"balance": 0, "referrer": None, "ref_credited": False, "verified": False}
    user_data[uid]["balance"] += 200
    save_data()
    bot.answer_callback_query(call.id, "₦200 added!")
    bot.edit_message_text("✅ ₦200 added to your balance. Check /balance.", call.message.chat.id, call.message.message_id)

# ---------- EXTRA TASK 2 (PEERPURSE) ----------
@bot.message_handler(commands=['jointask2'])
def jointask2(msg):
    uid = str(msg.from_user.id)
    if not is_verified(uid):
        send_verification_prompt(msg.chat.id, uid)
        return
    if uid not in user_data:
        user_data[uid] = {"balance": 0, "referrer": None, "ref_credited": False, "verified": False}
    bot.send_message(msg.chat.id,
        f"📌 **Task: Sign up on PeerPurse**\n\n"
        f"1. Use this referral code during signup: **{PEERPURSE_CODE}**\n"
        f"2. Complete your **KYC verification** (ID upload).\n"
        f"3. Once done, press the button below to claim ₦150.\n\n"
        f"⚠️ You must complete KYC to qualify.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("I've completed KYC ✅", callback_data=f"peerpurse_{uid}"))
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('peerpurse_'))
def peerpurse_done(call):
    uid = str(call.from_user.id)
    if not is_verified(uid):
        bot.answer_callback_query(call.id, "Please complete verification first.")
        return
    if uid not in user_data:
        user_data[uid] = {"balance": 0, "referrer": None, "ref_credited": False, "verified": False}
    user_data[uid]["balance"] += 150
    save_data()
    bot.answer_callback_query(call.id, "₦150 added!")
    bot.edit_message_text("✅ ₦150 added. Check /balance.", call.message.chat.id, call.message.message_id)

print("Bot running 24/7...")
bot.polling(none_stop=True)
