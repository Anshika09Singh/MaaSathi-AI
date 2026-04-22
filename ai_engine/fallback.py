def fallback_response(user_input, retrieved_docs, extra=None):
    query = user_input.lower()
    
    if "cook" in query or "meal" in query or "eat" in query:
        return (
            "Summary: I am using fallback mode for meal planning.\n"
            "Priority Actions:\n"
            "- Use vegetables, pulses, and one-pot meals.\n"
            "- Choose meals that are quick and high in protein.\n"
            "Next Step: Share your available ingredients for a more specific meal plan."
        )
    if "task" in query or "balance" in query or "assign" in query or "manage" in query:
        return (
            "Summary: I am using fallback mode for task planning.\n"
            "Priority Actions:\n"
            "- Split duties by urgency and energy.\n"
            "- Let one guardian handle urgent child care.\n"
            "- Let the other manage cooking and shopping.\n"
            "Next Step: Ask me for a day routine or workload balance."
        )
    if "safety" in query or "sos" in query or "alert" in query:
        return (
            "Immediate Action:\n"
            "- Move to a secure location.\n"
            "- Inform a trusted contact.\n"
            "Safety Checks:\n"
            "- Keep emergency numbers visible.\n"
            "- Stay reachable.\n"
            "Next Step: Call emergency support if the situation is urgent."
        )
        
    return (
        "Summary: The assistant is using fallback mode.\n"
        "Priority Actions:\n"
        "- I can still help with planning, reminders, and safety.\n"
        "- Ask for a routine plan, meal plan, or urgent next step.\n"
        "Next Step: Connect the AI provider for full contextual support."
    )
