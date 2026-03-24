import 'package:flutter/material.dart';
import 'package:genui/genui.dart';
import 'package:json_schema_builder/json_schema_builder.dart';

/// Custom XPost (X/Twitter) catalog item for the genui renderer.
final xPostItem = CatalogItem(
  name: 'XPost',
  dataSchema: S.object(
    description: 'An X/Twitter-style post card.',
    properties: {
      'authorName': S.string(description: 'Display name.'),
      'authorHandle': S.string(description: 'Handle (e.g. @user).'),
      'authorAvatarUrl': S.string(description: 'Author avatar URL.'),
      'verified': S.boolean(description: 'Verified badge.'),
      'body': S.string(description: 'Post body text.'),
      'mediaChild': S.string(description: 'ID of media child component.'),
      'replies': S.integer(description: 'Number of replies.'),
      'reposts': S.integer(description: 'Number of reposts.'),
      'likes': S.integer(description: 'Number of likes.'),
      'views': S.integer(description: 'Number of views.'),
    },
    required: ['authorName', 'authorHandle', 'body'],
  ),
  widgetBuilder: (CatalogItemContext ctx) {
    final data = ctx.data as JsonMap;
    final displayName = data['authorName'] as String? ?? '';
    final handle = data['authorHandle'] as String? ?? '';
    final avatarUrl = data['authorAvatarUrl'] as String?;
    final verified = data['verified'] as bool? ?? false;
    final body = data['body'] as String? ?? '';
    final likes = data['likes'] as int? ?? 0;
    final reposts = data['reposts'] as int? ?? 0;
    final replies = data['replies'] as int? ?? 0;
    final views = data['views'] as int? ?? 0;
    final mediaChildId = data['mediaChild'] as String?;

    return _XPostWidget(
      displayName: displayName,
      handle: handle,
      avatarUrl: avatarUrl,
      verified: verified,
      body: body,
      likes: likes,
      reposts: reposts,
      replies: replies,
      views: views,
      mediaChildId: mediaChildId,
      buildChild: ctx.buildChild,
    );
  },
);

class _XPostWidget extends StatelessWidget {
  final String displayName;
  final String handle;
  final String? avatarUrl;
  final bool verified;
  final String body;
  final int likes;
  final int reposts;
  final int replies;
  final int views;
  final String? mediaChildId;
  final ChildBuilderCallback buildChild;

  const _XPostWidget({
    required this.displayName,
    required this.handle,
    required this.avatarUrl,
    required this.verified,
    required this.body,
    required this.likes,
    required this.reposts,
    required this.replies,
    required this.views,
    required this.mediaChildId,
    required this.buildChild,
  });

  String _formatNumber(int n) {
    if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}K';
    return '$n';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.black,
        border: Border.all(color: const Color(0xFF2F3336)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  radius: 20,
                  backgroundColor: const Color(0xFF2F3336),
                  backgroundImage: avatarUrl != null && avatarUrl!.isNotEmpty
                      ? NetworkImage(avatarUrl!)
                      : null,
                  child: avatarUrl == null || avatarUrl!.isEmpty
                      ? Text(
                          displayName.isNotEmpty ? displayName[0].toUpperCase() : '?',
                          style: const TextStyle(color: Color(0xFFE7E9EA), fontWeight: FontWeight.bold),
                        )
                      : null,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Row(
                    children: [
                      Text(displayName,
                          style: const TextStyle(
                              color: Color(0xFFE7E9EA), fontWeight: FontWeight.w700, fontSize: 15, height: 1.33)),
                      if (verified) ...[
                        const SizedBox(width: 4),
                        const Icon(Icons.verified, size: 16, color: Color(0xFF1D9BF0)),
                      ],
                      const SizedBox(width: 4),
                      Text(handle.startsWith('@') ? handle : '@$handle',
                          style: const TextStyle(color: Color(0xFF71767B), fontSize: 15, height: 1.33)),
                      const Text(' \u00b7 ', style: TextStyle(color: Color(0xFF71767B), fontSize: 15)),
                      const Text('1h', style: TextStyle(color: Color(0xFF71767B), fontSize: 15)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // Body
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
            child: Text(body,
                style: const TextStyle(color: Color(0xFFE7E9EA), fontSize: 15, height: 1.33)),
          ),
          // Media child
          // Media child — stretch to full width
          if (mediaChildId != null)
            SizedBox(
              width: double.infinity,
              child: buildChild(mediaChildId!),
            ),
          // Engagement
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _engagementItem(Icons.chat_bubble_outline, _formatNumber(replies)),
                _engagementItem(Icons.repeat, _formatNumber(reposts)),
                _engagementItem(Icons.favorite_outline, _formatNumber(likes)),
                _engagementItem(Icons.bar_chart, _formatNumber(views)),
                const Icon(Icons.bookmark_border, size: 16, color: Color(0xFF71767B)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _engagementItem(IconData icon, String count) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: const Color(0xFF71767B)),
        const SizedBox(width: 4),
        Text(count, style: const TextStyle(color: Color(0xFF71767B), fontSize: 13)),
      ],
    );
  }
}
