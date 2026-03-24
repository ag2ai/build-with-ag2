import 'dart:async';

import 'package:flutter/material.dart';
import 'package:genui/genui.dart';
import 'package:genui_a2a/genui_a2a.dart';
import 'package:logging/logging.dart';
import 'package:provider/provider.dart';

import 'state/chat_state.dart';
import 'widgets/chat_screen.dart';
import 'widgets/custom/linkedin_post_item.dart';
import 'widgets/custom/x_post_item.dart';

void main() {
  Logger.root.level = Level.INFO;
  Logger.root.onRecord.listen((record) {
    debugPrint('${record.level.name}: ${record.time}: ${record.message}');
  });

  runApp(const A2UIDemoApp());
}

class A2UIDemoApp extends StatefulWidget {
  const A2UIDemoApp({super.key});

  @override
  State<A2UIDemoApp> createState() => _A2UIDemoAppState();
}

class _A2UIDemoAppState extends State<A2UIDemoApp> {
  late final A2uiAgentConnector _connector;
  late final SurfaceController _controller;
  late final A2uiTransportAdapter _transport;
  late final Conversation _conversation;
  late final StreamSubscription<A2uiMessage> _messageSubscription;
  late final StreamSubscription<String> _textSubscription;

  @override
  void initState() {
    super.initState();

    // Build the catalog with core items + custom components.
    // Register under multiple catalog IDs since the LLM may use different ones.
    final customItems = [linkedInPostItem, xPostItem];
    final socialCatalog = BasicCatalogItems.asCatalog().copyWith(
      newItems: customItems,
      catalogId: 'https://ag2.ai/a2ui/social_catalog.json',
    );
    final genericCatalog = BasicCatalogItems.asCatalog().copyWith(
      newItems: customItems,
      catalogId: 'https://ag2.ai/a2ui/catalog.json',
    );
    // Also keep the standard catalog for any surfaces that use it
    final standardCatalog = BasicCatalogItems.asCatalog().copyWith(
      newItems: customItems,
    );

    _controller = SurfaceController(catalogs: [socialCatalog, genericCatalog, standardCatalog]);

    _transport = A2uiTransportAdapter(
      onSend: _sendMessageToAgent,
    );

    _connector = A2uiAgentConnector(
      url: Uri.parse('http://localhost:9000'),
    );

    _conversation = Conversation(
      controller: _controller,
      transport: _transport,
    );

    // Pipe connector outputs to transport
    _messageSubscription = _connector.stream.listen(_transport.addMessage);
    _textSubscription = _connector.textStream.listen(_transport.addChunk);
  }

  Future<void> _sendMessageToAgent(ChatMessage message) async {
    await _connector.connectAndSend(
      message,
      clientCapabilities: _controller.clientCapabilities,
    );
  }

  @override
  void dispose() {
    _messageSubscription.cancel();
    _textSubscription.cancel();
    _conversation.dispose();
    _transport.dispose();
    _controller.dispose();
    _connector.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ChatState(conversation: _conversation),
      child: MaterialApp(
        title: 'A2UI Demo',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          brightness: Brightness.dark,
          scaffoldBackgroundColor: const Color(0xFF14182C),
          colorScheme: const ColorScheme.dark(
            primary: Color(0xFF4B9CD6),       // AG2 blue
            secondary: Color(0xFF526CFE),     // AG2 indigo
            surface: Color(0xFF14182C),
            onSurface: Color(0xFFF0F4F8),
          ),
          textTheme: const TextTheme(
            headlineLarge: TextStyle(color: Color(0xFF0D1B3C)),  // h1
            headlineMedium: TextStyle(color: Color(0xFF0D1B3C)), // h2
            headlineSmall: TextStyle(color: Color(0xFF0D1B3C)),  // h3
            titleLarge: TextStyle(color: Color(0xFF0D1B3C)),     // h4
            titleMedium: TextStyle(color: Color(0xFF0D1B3C)),    // h5
          ),
          appBarTheme: const AppBarTheme(
            backgroundColor: Color(0xFF14182C),
            elevation: 0,
          ),
          radioTheme: RadioThemeData(
            fillColor: WidgetStateProperty.all(const Color(0xFF0D1B3C)),
          ),
          listTileTheme: const ListTileThemeData(
            textColor: Color(0xFF0D1B3C),
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF4B9CD6),
              foregroundColor: const Color(0xFF0D1117),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(3)),
              side: const BorderSide(color: Color(0xFF4B9CD6), width: 2),
            ),
          ),
          textButtonTheme: TextButtonThemeData(
            style: TextButton.styleFrom(
              foregroundColor: const Color(0xFF4B9CD6),
            ),
          ),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: const Color(0x4D000000),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(3),
              borderSide: const BorderSide(color: Color(0x334B9CD6)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(3),
              borderSide: const BorderSide(color: Color(0x334B9CD6)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(3),
              borderSide: const BorderSide(color: Color(0xFF4B9CD6)),
            ),
          ),
        ),
        home: const ChatScreen(),
      ),
    );
  }
}
