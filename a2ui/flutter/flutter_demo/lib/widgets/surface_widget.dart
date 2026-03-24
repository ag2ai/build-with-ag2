import 'package:flutter/material.dart';
import 'package:genui/genui.dart';
import 'package:provider/provider.dart';

import '../state/chat_state.dart';

/// Renders an A2UI surface using the genui Surface widget.
class SurfaceWidget extends StatelessWidget {
  final String surfaceId;

  const SurfaceWidget({super.key, required this.surfaceId});

  @override
  Widget build(BuildContext context) {
    final state = context.read<ChatState>();
    final surfaceContext = state.conversation.controller.contextFor(surfaceId);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xF2F0F6FB), // light blue-white, ~95% opaque
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: const Color(0x404B9CD6), width: 2),
      ),
      child: Surface(
        surfaceContext: surfaceContext,
      ),
    );
  }
}
