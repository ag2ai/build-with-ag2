/// Represents a message in the chat list.
sealed class AppChatMessage {
  const AppChatMessage();
}

/// A text message from the user.
class UserMessage extends AppChatMessage {
  final String text;
  const UserMessage(this.text);
}

/// A text message from the bot/agent.
class BotMessage extends AppChatMessage {
  final String text;
  const BotMessage(this.text);
}

/// A reference to an A2UI surface to render inline.
class SurfaceMessage extends AppChatMessage {
  final String surfaceId;
  const SurfaceMessage(this.surfaceId);
}
