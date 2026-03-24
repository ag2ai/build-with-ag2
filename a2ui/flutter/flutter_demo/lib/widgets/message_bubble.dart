import 'package:flutter/material.dart';

class MessageBubble extends StatelessWidget {
  final String text;
  final bool isUser;

  const MessageBubble({super.key, required this.text, required this.isUser});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: isUser ? const Color(0xFF526CFE) : const Color(0x264B9CD6),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: isUser ? const Color(0x80526CFE) : const Color(0x404B9CD6),
            width: 2,
          ),
        ),
        child: Text(
          text,
          style: const TextStyle(
            color: Color(0xFFF0F4F8),
            fontSize: 14,
            height: 1.6,
          ),
        ),
      ),
    );
  }
}
