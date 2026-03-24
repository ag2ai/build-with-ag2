import 'package:flutter/material.dart';
import 'package:genui/genui.dart';
import 'package:json_schema_builder/json_schema_builder.dart';

/// Custom LinkedInPost catalog item for the genui renderer.
final linkedInPostItem = CatalogItem(
  name: 'LinkedInPost',
  dataSchema: S.object(
    description: 'A LinkedIn-style social media post card.',
    properties: {
      'authorName': S.string(description: 'Display name of the post author.'),
      'authorHeadline': S.string(description: 'Author headline.'),
      'authorAvatarUrl': S.string(description: 'Author avatar URL.'),
      'body': S.string(description: 'Post body text.'),
      'hashtags': S.string(description: 'Hashtag string.'),
      'mediaChild': S.string(description: 'ID of media child component.'),
      'likes': S.integer(description: 'Number of likes.'),
      'comments': S.integer(description: 'Number of comments.'),
      'reposts': S.integer(description: 'Number of reposts.'),
    },
    required: ['authorName', 'body'],
  ),
  widgetBuilder: (CatalogItemContext ctx) {
    final data = ctx.data as JsonMap;
    final authorName = data['authorName'] as String? ?? '';
    final authorHeadline = data['authorHeadline'] as String? ?? '';
    final avatarUrl = data['authorAvatarUrl'] as String?;
    final body = data['body'] as String? ?? '';
    final hashtagsRaw = data['hashtags'];
    final hashtags = hashtagsRaw is String
        ? hashtagsRaw.split(' ').where((s) => s.isNotEmpty).toList()
        : (hashtagsRaw is List ? hashtagsRaw.cast<String>() : <String>[]);
    final likes = data['likes'] as int? ?? 0;
    final comments = data['comments'] as int? ?? 0;
    final reposts = data['reposts'] as int? ?? 0;
    final mediaChildId = data['mediaChild'] as String?;

    return _LinkedInPostWidget(
      authorName: authorName,
      authorHeadline: authorHeadline,
      avatarUrl: avatarUrl,
      body: body,
      hashtags: hashtags,
      likes: likes,
      comments: comments,
      reposts: reposts,
      mediaChildId: mediaChildId,
      buildChild: ctx.buildChild,
    );
  },
);

class _LinkedInPostWidget extends StatelessWidget {
  final String authorName;
  final String authorHeadline;
  final String? avatarUrl;
  final String body;
  final List<String> hashtags;
  final int likes;
  final int comments;
  final int reposts;
  final String? mediaChildId;
  final ChildBuilderCallback buildChild;

  const _LinkedInPostWidget({
    required this.authorName,
    required this.authorHeadline,
    required this.avatarUrl,
    required this.body,
    required this.hashtags,
    required this.likes,
    required this.comments,
    required this.reposts,
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
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 0, spreadRadius: 1),
          BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 3, offset: const Offset(0, 2)),
        ],
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
                  radius: 24,
                  backgroundColor: const Color(0xFFE0E0E0),
                  backgroundImage: avatarUrl != null && avatarUrl!.isNotEmpty
                      ? NetworkImage(avatarUrl!)
                      : null,
                  child: avatarUrl == null || avatarUrl!.isEmpty
                      ? Text(
                          authorName.isNotEmpty ? authorName[0].toUpperCase() : '?',
                          style: const TextStyle(
                            color: Color(0xFF666666),
                            fontWeight: FontWeight.bold,
                            fontSize: 18,
                          ),
                        )
                      : null,
                ),
                const SizedBox(width: 8),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(authorName,
                        style: const TextStyle(
                            color: Color(0xE5000000), fontWeight: FontWeight.w600, fontSize: 16, height: 1.25)),
                    if (authorHeadline.isNotEmpty)
                      Text(authorHeadline,
                          style: const TextStyle(color: Color(0x99000000), fontSize: 12, height: 1.33)),
                    const Text('1d \u00b7 \ud83c\udf10',
                        style: TextStyle(color: Color(0x99000000), fontSize: 12, height: 1.33)),
                  ],
                ),
              ],
            ),
          ),
          // Body
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Text(body,
                style: const TextStyle(color: Color(0xE5000000), fontSize: 14, height: 1.43)),
          ),
          // Hashtags
          if (hashtags.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
              child: Text(
                hashtags.map((h) => h.startsWith('#') ? h : '#$h').join(' '),
                style: const TextStyle(
                    color: Color(0xFF0A66C2), fontSize: 14, fontWeight: FontWeight.w600, height: 1.43),
              ),
            ),
          // Media child — stretch to full width
          if (mediaChildId != null) ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: buildChild(mediaChildId!),
            ),
          ],
          // Engagement counts
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: Row(
              children: [
                const Text('\ud83d\udc4d ', style: TextStyle(fontSize: 12)),
                Text(_formatNumber(likes),
                    style: const TextStyle(color: Color(0x99000000), fontSize: 12)),
                const Text(' \u00b7 ', style: TextStyle(color: Color(0x99000000), fontSize: 12)),
                Text('${_formatNumber(comments)} comments',
                    style: const TextStyle(color: Color(0x99000000), fontSize: 12)),
                const Text(' \u00b7 ', style: TextStyle(color: Color(0x99000000), fontSize: 12)),
                Text('${_formatNumber(reposts)} reposts',
                    style: const TextStyle(color: Color(0x99000000), fontSize: 12)),
              ],
            ),
          ),
          // Action buttons
          Container(
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: Color(0xFFE0E0E0), width: 1)),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            child: Row(
              children: [
                _actionButton(Icons.thumb_up_outlined, 'Like'),
                _actionButton(Icons.comment_outlined, 'Comment'),
                _actionButton(Icons.repeat, 'Repost'),
                _actionButton(Icons.send_outlined, 'Send'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _actionButton(IconData icon, String label) {
    return Expanded(
      child: TextButton.icon(
        onPressed: null,
        icon: Icon(icon, size: 18, color: const Color(0x99000000)),
        label: Text(label,
            style: const TextStyle(color: Color(0x99000000), fontSize: 14, fontWeight: FontWeight.w600)),
      ),
    );
  }
}
