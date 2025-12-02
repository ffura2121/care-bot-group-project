import asyncio
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import db
from config import BOT_TOKEN
from sentiment import analyze_text

# Логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("carebot")

# FSM
class MoodStates(StatesGroup):
    waiting_for_text = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Кнопки для нейтрального настрою та /relax (додані методи)
relax_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Дихальні вправи", callback_data="relax_breath")],
    [InlineKeyboardButton(text="Релакс-музика", callback_data="relax_music")],
    [InlineKeyboardButton(text="Міні-вправа (2 хв)", callback_data="relax_ex")],
    [InlineKeyboardButton(text="Заземлення 5-4-3-2-1", callback_data="relax_grounding")],
    [InlineKeyboardButton(text="Сканування тіла", callback_data="relax_body_scan")]
])


# =======================
#      ХЕНДЛЕРИ
# =======================

@router.message(Command("start"))
async def cmd_start(message: Message):
    await db.init_db()
    logger.info(f"/start від {message.from_user.id} ({message.from_user.username})")
    await message.answer(
        "Привіт! Я CareBot — AI-помічник для психологічної підтримки.\n\n"
        "Команди:\n"
        "/mood — поділитися почуттями\n"
        "/diary — переглянути емоційний щоденник\n"
        "/relax — техніки релаксації\n"
        "/contact — контакти спеціалістів\n"
        "/help — допомога"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    logger.info(f"/help від {message.from_user.id}")
    await message.answer("Я аналізую ваш текст і допомагаю заспокоїтись. Використайте /mood.")


@router.message(Command("mood"))
async def cmd_mood(message: Message, state: FSMContext):
    logger.info(f"/mood від {message.from_user.id}")
    await message.answer("Розкажіть, будь ласка, як ви почуваєтесь зараз.")
    await state.set_state(MoodStates.waiting_for_text)


@router.message(MoodStates.waiting_for_text)
async def handle_mood_text(message: Message, state: FSMContext):
    text = message.text or ""
    label, score = analyze_text(text)

    # Зберегти в БД
    await db.save_emotion(
        message.from_user.id,
        message.from_user.username or "",
        text,
        label,
        score
    )

    logger.info(f"Аналіз тексту від {message.from_user.id}: '{text[:50]}...' → {label} {score:.2f}")

    # =============================
    #     РОЗГАЛУЖЕННЯ ВІДПОВІДЕЙ
    # =============================

    # 1. ПОЗИТИВНИЙ НАСТРІЙ — БЕЗ КЛАВІАТУРИ
    if label == "positive":
        reply = (
            f"😊 Я дуже радий чути, що у вас чудовий настрій! (score={score:.2f})\n\n"
            "Щоб підтримати спокій — ось легка релакс-музика:\n"
            "https://youtu.be/2OEL4P1Rz04\n\n"
            "Продовжуйте в тому ж дусі!"
        )
        await message.answer(reply)

    # 2. НЕЙТРАЛЬНИЙ — КЛАВІАТУРА ЗАЛИШАЄТЬСЯ
    elif label == "neutral":
        reply = (
            f"🙂 Дякую, що поділилися. (score={score:.2f})\n\n"
            "Оберіть один із способів розслабитися:"
        )
        await message.answer(reply, reply_markup=relax_kb)

    # 3. НЕГАТИВНИЙ — СПОЧАТКУ ТЕКСТ, ПОТІМ КНОПКИ, ПОТІМ КОНТАКТИ
    else:
        # 3.1 Емпатичний текст (першим)
        bad_text = (
            f"😔 Мені дуже шкода, що вам зараз важко. (score={score:.2f})\n\n"
            "Ось кілька технік, які можуть допомогти вам стабілізувати емоції:\n"
            "1️⃣ Дихальна техніка 4-7-8\n"
            "2️⃣ Заземлення 5-4-3-2-1\n"
            "3️⃣ Релакс-музика: https://youtu.be/2OEL4P1Rz04\n"
            "4️⃣ Міні-вправа: повільне розтягнення плечей і шиї\n"
            "5️⃣ Стисніть і відпустіть кулаки 10 разів\n"
            "6️⃣ Сканування тіла\n"
            "7️⃣ Повільне пиття води\n\n"
            "Ви не самі. Я поряд."
        )
        await message.answer(bad_text)

        logger.info(f"Негативний настрій від {message.from_user.id} — відправлено підтримку.")

        # 3.2 Потім надсилаємо клавіатуру зі скриптом технік (щоб користувач міг обрати детально)
        await message.answer("Оберіть техніку, щоб отримати інструкцію:", reply_markup=relax_kb)

        # 3.3 Потім автоматично надсилаємо контакти (як алгоритм — форматований блок)
        await cmd_contact(message)

    await state.clear()


@router.message(Command("diary"))
async def cmd_diary(message: Message):
    logger.info(f"/diary від {message.from_user.id}")
    rows = await db.get_recent(message.from_user.id, limit=8)
    if not rows:
        await message.answer("Поки немає записів. Використайте /mood.")
        return

    txt = "Останні записи:\n\n"
    for text, sentiment, score, created in rows:
        short = (text[:120] + "...") if len(text) > 120 else text
        txt += f"{created} — [{sentiment} {score:.2f}] {short}\n\n"

    await message.answer(txt)


@router.message(Command("relax"))
async def cmd_relax(message: Message):
    logger.info(f"/relax від {message.from_user.id}")
    await message.answer(
        "Оберіть техніку релаксації:",
        reply_markup=relax_kb
    )


@router.callback_query(lambda c: c.data and c.data.startswith("relax_"))
async def cb_relax(query: CallbackQuery):
    logger.info(f"Callback {query.data} від {query.from_user.id}")

    if query.data == "relax_breath":
        await query.message.answer("Вправа 4-4-4: вдих 4с, затримка 4с, видих 4с × 5 разів.")

    elif query.data == "relax_music":
        await query.message.answer("Релакс-музика: https://youtu.be/2OEL4P1Rz04")

    elif query.data == "relax_ex":
        await query.message.answer("Міні-вправа: закрийте очі та 2 хвилини дихайте повільно.")

    elif query.data == "relax_grounding":
        await query.message.answer(
            "Заземлення 5-4-3-2-1:\n"
            "• Назвіть 5 предметів, які бачите.\n"
            "• Почуйте 4 звуки.\n"
            "• Торкніться 3 речей.\n"
            "• Замисліться про 2 запахи.\n"
            "• Згадайте 1 приємний спогад."
        )

    elif query.data == "relax_body_scan":
        await query.message.answer(
            "Сканування тіла: повільно пройдіться увагою від голови до ніг, "
            "відчуваючи і розслабляючи кожну ділянку."
        )

    await query.answer()


@router.message(Command("contact"))
async def cmd_contact(message: Message):
    """
    Відправляє контакти у вигляді форматованого блоку (алгоритм): 
    показує важливу інформацію — номер психолога, лінію допомоги та попередження.
    """
    logger.info(f"/contact від {message.from_user.id}")
    await message.answer(
        "Контакти:\n"
        "• Психолог — +380 99 000 00 00\n"
        "• Лінія допомоги — 7333\n\n"
        "Якщо є ризик — негайно телефонуйте!"
    )


# =======================
#       MAIN
# =======================

async def main():
    logger.info("BOT STARTED")
    dp.include_router(router)

    try:
        await dp.start_polling(bot)

    except asyncio.CancelledError:
        logger.warning("Polling cancelled (CancelledError).")

    except KeyboardInterrupt:
        logger.info("Bot stopped manually (KeyboardInterrupt).")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    finally:
        await bot.session.close()
        logger.info("BOT STOPPED")

if __name__ == "__main__":
    asyncio.run(main())
