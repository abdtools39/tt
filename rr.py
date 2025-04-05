import telebot
from telebot import types
import time
import smtplib

# Configuration (Replace with your actual values)
BOT_TOKEN = "8101038299:AAFkJOEdQDGhtvTzUuHiHc-HJol_ntk9a-U"  # Replace with your bot token
ADMIN_ID = 5347602862  # Replace with your admin user ID
USERS_FILE = "users.json"
SESSION_FILE = "sessions.json"
#CHANNEL_USERNAME = "@your_channel" # This is not used anymore


bot = telebot.TeleBot(BOT_TOKEN)
users = {}
sessions = {}
sending_status = {}

def save_data(data, filename):
    import json
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data(filename):
    import json
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

users = load_data(USERS_FILE)
sessions = load_data(SESSION_FILE)



def is_vip(user_id):
    user_id = str(user_id)
    return users.get(user_id, {}).get("vip", False)


def timeCalc(days):
    import datetime
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    endTime = (datetime.datetime.now() + datetime.timedelta(days=days)).timestamp()
    return {
        "current_date": current_date,
        "end_date": end_date,
        "endTime": endTime
    }


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID and users.get(str(user_id)) is None:
        users[str(user_id)] = {"vip": True}
        save_data(users, USERS_FILE)
    if str(user_id) in sessions:
        bot.reply_to(
            message,
            "مرحباً مجدداً! يمكنك الآن إرسال بريد إلكتروني عبر كتابة 'send'.")
    else:
        bot.reply_to(
            message,
            "أهلاً! الرجاء إرسال بريدك الإلكتروني وكلمة مرور التطبيق بصيغة: \nemail,password"
        )


@bot.message_handler(commands=['addvip'])
def add_vip(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "هذا الأمر متاح للمشرفين فقط.")

    try:
        user_id, days = message.text.split()[1:]
        user_id = str(user_id)
        days = int(days)

        vip_date = timeCalc(days)
        users[user_id] = {
            "vip": True,
            "limitation": {
                "days": days,
                "startDate": vip_date["current_date"],
                "endDate": vip_date["end_date"],
                "endTime": vip_date["endTime"]
            }
        }
        save_data(users, USERS_FILE)

        caption = f"تم تفعيل VIP للمستخدم {user_id}\n"
        caption += f"تاريخ البدء: {vip_date['current_date']}\n"
        caption += f"تاريخ الانتهاء: {vip_date['end_date']}\n"
        caption += f"المدة: {days} يوم"

        bot.reply_to(message, caption)
        try:
            bot.send_message(int(user_id),
                             f"تم تفعيل اشتراك VIP لحسابك!\n{caption}")
        except:
            bot.reply_to(message, "تم التفعيل لكن تعذر إرسال رسالة للمستخدم")

    except Exception as e:
        bot.reply_to(message,
                     "خطأ في الأمر. الصيغة الصحيحة:\n/addvip USER_ID DAYS")


@bot.message_handler(
    func=lambda message: "," in message.text and "@" in message.text)
def save_credentials(message):
    if not is_vip(message.from_user.id):
        return bot.reply_to(message,
                            "عذراً، هذه الخدمة متاحة فقط للمشتركين VIP.")

    email, password = message.text.split(",")
    user_id = str(message.chat.id)
    if user_id not in sessions:
        sessions[user_id] = {}
    sessions[user_id]["email"] = email.strip()
    sessions[user_id]["password"] = password.strip()
    save_data(sessions, SESSION_FILE)
    bot.reply_to(message, "تم حفظ معلومات حسابك بنجاح. ارسل Send الانٍ")


@bot.callback_query_handler(func=lambda call: call.data == "stop_sending")
def stop_sending_callback(call):
    chat_id = str(call.message.chat.id)  # تحويل الـ chat_id إلى نص
    sending_status[chat_id] = False
    bot.answer_callback_query(call.id, "جارِ إيقاف الإرسال...")
    bot.edit_message_text("تم إيقاف الإرسال ✋",
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id)


@bot.message_handler(func=lambda message: str(message.chat.id) in sessions and
                     message.text.lower() == "send")
def request_target_email(message):
    if not is_vip(message.from_user.id):
        return bot.reply_to(message,
                            "عذراً، هذه الخدمة متاحة فقط للمشتركين VIP.")

    bot.reply_to(message, "أرسل البريد المستهدف")
    sessions[str(message.chat.id)]["step"] = "target_email"
    save_data(sessions, SESSION_FILE)


@bot.message_handler(
    func=lambda message: str(message.chat.id) in sessions and sessions[str(
        message.chat.id)].get("step") == "target_email")
def request_subject(message):
    if not is_vip(message.from_user.id):
        return bot.reply_to(message,
                            "عذراً، هذه الخدمة متاحة فقط للمشتركين VIP.")

    sessions[str(message.chat.id)]["target_email"] = message.text.strip()
    sessions[str(message.chat.id)]["step"] = "subject"
    save_data(sessions, SESSION_FILE)
    bot.reply_to(message, "الآن أرسل موضوع الرسالة")


@bot.message_handler(func=lambda message: str(message.chat.id) in sessions and
                     sessions[str(message.chat.id)].get("step") == "subject")
def request_message_body(message):
    if not is_vip(message.from_user.id):
        return bot.reply_to(message,
                            "عذراً، هذه الخدمة متاحة فقط للمشتركين VIP.")

    sessions[str(message.chat.id)]["subject"] = message.text.strip()
    sessions[str(message.chat.id)]["step"] = "message_body"
    save_data(sessions, SESSION_FILE)
    bot.reply_to(message, "الآن أرسل نص الرسالة")


@bot.message_handler(
    func=lambda message: str(message.chat.id) in sessions and sessions[str(
        message.chat.id)].get("step") == "message_body")
def request_message_count(message):
    if not is_vip(message.from_user.id):
        return bot.reply_to(message,
                            "عذراً، هذه الخدمة متاحة فقط للمشتركين VIP.")

    sessions[str(message.chat.id)]["message_body"] = message.text.strip()
    sessions[str(message.chat.id)]["step"] = "num_messages"
    save_data(sessions, SESSION_FILE)
    bot.reply_to(message, "أخيراً، أرسل عدد الرسائل المراد إرسالها")


@bot.message_handler(func=lambda message: str(
    message.chat.id) in sessions and sessions[str(message.chat.id)].get("step")
                     == "num_messages" and message.text.isdigit())
def request_delay_time(message):
    if not is_vip(message.from_user.id):
        return bot.reply_to(message,
                            "عذراً، هذه الخدمة متاحة فقط للمشتركين VIP.")

    chat_id = str(message.chat.id)
    sessions[chat_id]["num_messages"] = int(message.text.strip())
    sessions[chat_id]["step"] = "delay_time"
    save_data(sessions, SESSION_FILE)
    bot.reply_to(message, "أدخل عدد الثواني بين كل إرسال:")


@bot.message_handler(func=lambda message: str(
    message.chat.id) in sessions and sessions[str(message.chat.id)].get("step")
                     == "delay_time" and message.text.isdigit())
def start_sending_emails(message):
    if not is_vip(message.from_user.id):
        return bot.reply_to(message,
                            "عذراً، هذه الخدمة متاحة فقط للمشتركين VIP.")

    chat_id = str(message.chat.id)
    sessions[chat_id]["delay_time"] = int(message.text.strip())
    sessions[chat_id]["step"] = None
    save_data(sessions, SESSION_FILE)
    bot.reply_to(message, "جارٍ إرسال الرسائل...")
    send_emails(chat_id)



def send_emails(chat_id):
    chat_id_str = str(chat_id)  # تحويل الـ chat_id إلى نص
    data = sessions[chat_id_str]
    email_address = data["email"]
    email_password = data["password"]
    target_email = data["target_email"]
    subject = data["subject"]
    message_body = data["message_body"]
    num_messages = data["num_messages"]

    sending_status[chat_id] = True

    # إنشاء زر إيقاف الإرسال
    stop_markup = types.InlineKeyboardMarkup()
    stop_markup.add(
        types.InlineKeyboardButton("⏹ إيقاف الإرسال", callback_data="stop_sending"))

    # إرسال رسالة الحالة الأولية
    status_message = bot.send_message(chat_id,
                                      "جارِ إرسال الرسائل...\n0/" +
                                      str(num_messages),
                                      reply_markup=stop_markup)

    message = f"""Subject: {subject}\n\n{message_body}"""
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_address, email_password)

        for i in range(num_messages):
            if not sending_status.get(chat_id, False):
                bot.edit_message_text("تم إيقاف الإرسال ✋", chat_id,
                                      status_message.message_id)
                break

            server.sendmail(email_address, target_email, message)
            if i < num_messages - 1:  # لا داعي للتأخير بعد آخر رسالة
                time.sleep(data.get("delay_time", 0))
            # تحديث رسالة الحالة
            bot.edit_message_text(
                f"جارِ إرسال الرسائل...\n{i+1}/{num_messages}",
                chat_id,
                status_message.message_id,
                reply_markup=stop_markup)

        server.quit()
        if sending_status.get(chat_id, False):
            bot.edit_message_text("✅ اكتمل إرسال جميع الرسائل بنجاح!", chat_id,
                                  status_message.message_id)
    except Exception as e:
        bot.send_message(chat_id, f"حدث خطأ: {e}")

    # تنظيف البيانات
    for key in ["target_email", "subject", "message_body", "num_messages"]:
        if key in sessions[chat_id]:
            del sessions[chat_id][key]
    sessions[chat_id]["step"] = None
    save_data(sessions, SESSION_FILE)


bot.infinity_polling()
