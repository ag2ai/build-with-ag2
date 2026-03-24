import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/chat_message.dart';
import '../state/chat_state.dart';
import 'message_bubble.dart';
import 'surface_widget.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

const _demoPrompt = 'Create marketing previews for H2Oh, a premium reusable '
    'water bottle priced at \$39.\n\n'
    'Product details:\n'
    '- Vacuum-insulated stainless steel, keeps water cold for 24 hours\n'
    '- Leak-proof lid with one-hand open\n'
    '- Available in 5 colors: Ocean Blue, Slate Grey, Sage Green, Blush Pink, Matte Black\n'
    '- BPA-free, eco-friendly \u2014 replaces 300+ plastic bottles per year\n'
    '- Fits standard cup holders\n\n'
    'Brand details:\n'
    '- Author name: H2Oh\n'
    '- LinkedIn headline: 5,200 followers\n'
    '- X handle: @DrinkH2Oh (verified)\n\n'
    'Campaign: Launch email to eco-conscious consumers.\n'
    'Tone: Fresh, modern, sustainability-focused.\n'
    'CTA: Shop Now \u2014 Free Shipping on First Order';

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();

  void _send() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();
    context.read<ChatState>().sendMessage(text);
    _scrollToBottom();
  }

  void _sendDemoPrompt() {
    context.read<ChatState>().sendMessage(_demoPrompt);
    _scrollToBottom();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('A2UI Demo', style: TextStyle(fontWeight: FontWeight.w600)),
        centerTitle: true,
      ),
      body: Column(
        children: [
          Expanded(
            child: Consumer<ChatState>(
              builder: (context, state, _) {
                if (state.messages.isEmpty && !state.isLoading) {
                  return Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'A2UI Marketing Preview Demo',
                          style: TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 18,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: _sendDemoPrompt,
                          icon: const Icon(Icons.play_arrow),
                          label: const Text('Try Demo'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF6366F1),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                        ),
                      ],
                    ),
                  );
                }
                _scrollToBottom();
                return ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(16),
                  itemCount: state.messages.length + (state.isLoading ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index == state.messages.length) {
                      return const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12),
                        child: Center(
                          child: SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        ),
                      );
                    }
                    final msg = state.messages[index];
                    return switch (msg) {
                      UserMessage m => MessageBubble(text: m.text, isUser: true),
                      BotMessage m => MessageBubble(text: m.text, isUser: false),
                      SurfaceMessage m => SurfaceWidget(surfaceId: m.surfaceId),
                    };
                  },
                );
              },
            ),
          ),
          _buildInputBar(),
        ],
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      decoration: const BoxDecoration(
        color: Color(0xFF1E293B),
        border: Border(top: BorderSide(color: Color(0xFF334155))),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              style: const TextStyle(color: Color(0xFFE2E8F0)),
              decoration: const InputDecoration(
                hintText: 'Type a message...',
                hintStyle: TextStyle(color: Color(0xFF94A3B8)),
                contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
              onSubmitted: (_) => _send(),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: _send,
            icon: const Icon(Icons.send, color: Color(0xFF6366F1)),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}
