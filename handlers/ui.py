from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message, ReplyKeyboardRemove
import logging
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

    # Always delete the command message to keep chat clean
    try:
        await message.delete()
    except Exception:
        pass

    if config.BANNER_MENU.exists():
        try:
            await message.answer_photo(
                FSInputFile(config.BANNER_MENU),
                caption=text,
                reply_markup=kb,
            )
            return
        except Exception as e:
            logging.error(f"Failed to send menu banner: {e}")
            
    await message.answer(text, reply_markup=kb)


async def edit_screen(
    callback: CallbackQuery,
    text: str,
    markup,
    banner_path=None
) -> None:
    """Intelligently updates the current screen using edit_message_media or edit_message_caption."""
    try:
        if banner_path and banner_path.exists():
            media = InputMediaPhoto(media=FSInputFile(banner_path), caption=text)
            await callback.message.edit_media(media=media, reply_markup=markup)
        else:
            if callback.message.photo:
                await callback.message.edit_caption(caption=text, reply_markup=markup)
            else:
                await callback.message.edit_text(text, reply_markup=markup)
    except Exception as e:
        # If content hasn't changed or other error, just ignore
        logging.debug(f"Edit screen ignored/failed: {e}")
    finally:
        try:
            await callback.answer()
        except Exception:
            pass


async def edit_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    name = callback.from_user.full_name or "друг"
    text = welcome(name)
    kb = main_menu_inline()
    await edit_screen(callback, text, kb, banner_path=config.BANNER_MENU)


async def show_panel(callback: CallbackQuery, text: str, markup) -> None:
    # We fallback to the main menu banner if no specific panel banner is needed, 
    # or just edit the caption of the current banner.
    await edit_screen(callback, text, markup)
