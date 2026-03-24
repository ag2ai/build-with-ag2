import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/chat_message.dart';
import '../state/chat_state.dart';
import 'message_bubble.dart';
import 'surface_widget.dart';

// AG2 color palette
const _ag2Blue = Color(0xFF4B9CD6);
const _ag2Indigo = Color(0xFF526CFE);
const _panelBg = Color(0xEB14182C);
const _panelBorder = Color(0xFF4B9CD6);
const _textSecondary = Color(0xFFA0B4C8);

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
      body: Stack(
        children: [
          // Sky gradient background
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFFB5E8D5), // AG2 sky top
                  Color(0xFFD4F0E0),
                  Color(0xFFEEE8B0),
                  Color(0xFFF5E6A3), // AG2 sky bottom
                ],
                stops: [0.0, 0.3, 0.6, 1.0],
              ),
            ),
          ),
          // Pixel roadscape pinned to bottom
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Image.network(
              'http://localhost:9000/images/roadscape.png',
              fit: BoxFit.fitWidth,
              filterQuality: FilterQuality.none, // pixelated
              alignment: Alignment.bottomCenter,
              errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            ),
          ),
          // Chat content on top
          Column(
        children: [
          // Header with AG2 branding
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            decoration: const BoxDecoration(
              color: _panelBg,
              border: Border(bottom: BorderSide(color: _panelBorder, width: 2)),
            ),
            child: Row(
              children: [
                // Pixel robot avatar
                Image.network(
                  'http://localhost:9000/images/robot-blue.png',
                  width: 48,
                  height: 48,
                  filterQuality: FilterQuality.none, // pixelated rendering
                  errorBuilder: (_, __, ___) => const Icon(Icons.smart_toy, size: 48, color: _ag2Blue),
                ),
                const SizedBox(width: 16),
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'AG2 A2UIAgent',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                        color: _ag2Blue,
                        letterSpacing: 1,
                      ),
                    ),
                    Text(
                      'A2UI v0.9 \u00b7 Marketing Preview Designer',
                      style: TextStyle(fontSize: 12, color: _textSecondary),
                    ),
                  ],
                ),
                const Spacer(),
                // AG2 logo
                Image.network(
                  'http://localhost:9000/images/AG2-square.png',
                  width: 36,
                  height: 36,
                  filterQuality: FilterQuality.none,
                  errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                ),
              ],
            ),
          ),
          // Chat area
          Expanded(
            child: Consumer<ChatState>(
              builder: (context, state, _) {
                if (state.messages.isEmpty && !state.isLoading) {
                  return _buildWelcome();
                }
                return ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(20),
                  itemCount: state.messages.length + (state.isLoading ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index == state.messages.length) {
                      return const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12),
                        child: Center(
                          child: SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: _ag2Blue,
                            ),
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
        ], // Stack children
      ), // Stack
    );
  }

  Widget _buildWelcome() {
    return Align(
      alignment: const Alignment(0, -0.4), // push content above center
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Image.network(
            'http://localhost:9000/images/robot-blue.png',
            width: 100,
            height: 100,
            filterQuality: FilterQuality.none,
            errorBuilder: (_, __, ___) => const Icon(Icons.smart_toy, size: 100, color: _ag2Blue),
          ),
          const SizedBox(height: 16),
          const Text(
            'AG2 A2UIAgent Demo',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: _ag2Blue,
              letterSpacing: 1,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Generate rich marketing previews with A2UI v0.9',
            style: TextStyle(fontSize: 14, color: Color(0xFF2D3748)),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _sendDemoPrompt,
            icon: const Icon(Icons.play_arrow),
            label: const Text('Try Demo'),
            style: ElevatedButton.styleFrom(
              backgroundColor: _ag2Blue,
              foregroundColor: const Color(0xFF0D1117),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(3)),
              side: const BorderSide(color: _ag2Blue, width: 2),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(24, 12, 24, 16),
      decoration: const BoxDecoration(
        color: _panelBg,
        border: Border(top: BorderSide(color: _panelBorder, width: 2)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              style: const TextStyle(color: Color(0xFFF0F4F8), fontSize: 14),
              decoration: const InputDecoration(
                hintText: 'Type a message...',
                hintStyle: TextStyle(color: _textSecondary, fontSize: 14),
                contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
              onSubmitted: (_) => _send(),
            ),
          ),
          const SizedBox(width: 10),
          ElevatedButton(
            onPressed: _send,
            style: ElevatedButton.styleFrom(
              backgroundColor: _ag2Blue,
              foregroundColor: const Color(0xFF0D1117),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(3)),
              side: const BorderSide(color: _ag2Blue, width: 2),
            ),
            child: const Text('Send', style: TextStyle(fontWeight: FontWeight.w600, letterSpacing: 1)),
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
