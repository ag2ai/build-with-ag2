import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:genui/genui.dart';

import '../models/chat_message.dart';

class ChatState extends ChangeNotifier {
  final Conversation conversation;
  final List<AppChatMessage> messages = [];

  late final StreamSubscription<ConversationEvent> _eventSubscription;

  ChatState({required this.conversation}) {
    _eventSubscription = conversation.events.listen(_handleEvent);
  }

  bool get isLoading => conversation.state.value.isWaiting;

  void _handleEvent(ConversationEvent event) {
    switch (event) {
      case ConversationSurfaceAdded(:final surfaceId):
        messages.add(SurfaceMessage(surfaceId));
        notifyListeners();
      case ConversationContentReceived(:final text):
        if (text.isNotEmpty) {
          messages.add(BotMessage(text));
          notifyListeners();
        }
      case ConversationWaiting():
        notifyListeners();
      case _:
        notifyListeners();
    }
  }

  Future<void> sendMessage(String text) async {
    messages.add(UserMessage(text));
    notifyListeners();
    await conversation.sendRequest(ChatMessage.user(text));
  }

  @override
  void dispose() {
    _eventSubscription.cancel();
    super.dispose();
  }
}
