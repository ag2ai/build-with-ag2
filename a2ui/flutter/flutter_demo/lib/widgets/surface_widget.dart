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
      child: Surface(
        surfaceContext: surfaceContext,
      ),
    );
  }
}
