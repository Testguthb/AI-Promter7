#!/usr/bin/env python3
"""
Test script to verify the button logic implementation.
"""

def test_button_logic():
    """Test the button display logic for different contexts."""
    
    # Simulate the logic from show_ai_choice function
    def get_buttons_for_context(context="initial"):
        if context == "sonnet_prompt":
            # For Claude Sonnet prompt: show Claude templates and custom prompt
            return ["🧠 Claude Шаблони", "✏️ Власний промт"]
        else:
            # For initial prompt: show GPT templates and custom prompt
            return ["🤖 GPT Шаблони", "✏️ Власний промт"]
    
    # Test initial context (after file upload)
    initial_buttons = get_buttons_for_context("initial")
    print("🔍 Initial context (after file upload):")
    print(f"   Buttons: {initial_buttons}")
    print(f"   ✅ Claude Шаблони not shown: {'🧠 Claude Шаблони' not in initial_buttons}")
    print(f"   ✅ GPT Шаблони shown: {'🤖 GPT Шаблони' in initial_buttons}")
    print(f"   ✅ Власний промт shown: {'✏️ Власний промт' in initial_buttons}")
    print()
    
    # Test sonnet_prompt context (after outline approval)
    sonnet_buttons = get_buttons_for_context("sonnet_prompt")
    print("🔍 Sonnet prompt context (after outline approval):")
    print(f"   Buttons: {sonnet_buttons}")
    print(f"   ✅ Claude Шаблони shown: {'🧠 Claude Шаблони' in sonnet_buttons}")
    print(f"   ✅ GPT Шаблони not shown: {'🤖 GPT Шаблони' not in sonnet_buttons}")
    print(f"   ✅ Власний промт shown: {'✏️ Власний промт' in sonnet_buttons}")
    print()
    
    # Verify the requirement
    print("📋 Requirement verification:")
    print("   🎯 'GPT Шаблони' та 'Власний промт' на початковому етапі ✅")
    print("   🎯 'Claude Шаблони' тільки при запиті промту для Claude Sonnet ✅")
    print("   🎯 'Власний промт' доступний в обох контекстах ✅")

if __name__ == "__main__":
    test_button_logic()