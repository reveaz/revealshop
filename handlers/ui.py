from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message, ReplyKeyboardRemove

import config
from keyboards import main_menu_inline
from texts import welcome


async def remove_reply_keyboard(message: Message) -> None:
    msg = await message.answer("\u2063", reply_markup=ReplyKeyboardRemove())
    try:
        await msg.delete()
    except Exception:
        pass


async def send_home(message: Message, state: FSMContext, name: str | None = None) -> None:
    await state.clear()
    await remove_reply_keyboard(message)
    n = name or (message.from_user.full_name if message.from_user else "друг")
    text = welcome(n)
    kb = main_menu_inline()

    # Send banner photo if it exists
    if config.BANNER_MENU.exists():
        try:
            await message.answer_photo(
                FSInputFile(config.BANNER_MENU),
                caption=text,
                reply_markup=kb,
            )
            return
        except Exception as e:
            import logging
            logging.error(f"Failed to send menu banner: {e}")
    await message.answer(text, reply_markup=kb)


async def edit_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    name = callback.from_user.full_name or "друг"
    text = welcome(name)
    kb = main_menu_inline()

    # Can't edit text→photo, so delete old + send new
    if config.BANNER_MENU.exists():
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.message.answer_photo(
                FSInputFile(config.BANNER_MENU),
                caption=text,
                reply_markup=kb,
            )
            return
        except Exception:
            pass
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


async def show_panel(callback: CallbackQuery, text: str, markup) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()
