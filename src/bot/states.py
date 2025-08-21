from aiogram.fsm.state import State, StatesGroup


class ProcessingStates(StatesGroup):
    """FSM states for the bot workflow."""
    waiting_for_file = State()
    waiting_for_prompt = State()
    waiting_for_outline_approval = State()
    waiting_for_sonnet_prompt = State()
    waiting_for_volume_choice = State()

    # Template-related states
    waiting_for_ai_choice = State()
    waiting_for_gpt_folder_choice = State()
    waiting_for_template_choice = State()
    waiting_for_story_change_confirmation = State()
    waiting_for_new_story_text = State()
    waiting_for_story_generation = State()
    waiting_for_final_template_confirmation = State()

    processing = State()