import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

// Renders agent output (which is markdown — **bold**, `code`, ### headers,
// - bullets, line breaks) into themed, compact HTML. remark-breaks turns the
// agents' single newlines into real line breaks.

const COMPONENTS = {
  p: (props) => <p style={{ margin: '0 0 6px' }} {...props} />,
  strong: (props) => <strong style={{ color: 'var(--color-text-primary)', fontWeight: 600 }} {...props} />,
  em: (props) => <em {...props} />,
  a: (props) => <a style={{ color: 'var(--color-blue)' }} target="_blank" rel="noreferrer" {...props} />,
  ul: (props) => <ul style={{ margin: '4px 0', paddingLeft: 18 }} {...props} />,
  ol: (props) => <ol style={{ margin: '4px 0', paddingLeft: 18 }} {...props} />,
  li: (props) => <li style={{ margin: '2px 0' }} {...props} />,
  h1: (props) => <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', margin: '8px 0 3px' }} {...props} />,
  h2: (props) => <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', margin: '8px 0 3px' }} {...props} />,
  h3: (props) => <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', margin: '6px 0 3px' }} {...props} />,
  h4: (props) => <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', margin: '6px 0 3px' }} {...props} />,
  blockquote: (props) => (
    <blockquote style={{ margin: '4px 0', paddingLeft: 10, borderLeft: '2px solid var(--color-border)', color: 'var(--color-text-muted)' }} {...props} />
  ),
  code: (props) => (
    <code
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '0.92em',
        background: 'rgba(155,221,255,0.10)',
        color: 'var(--color-blue)',
        padding: '1px 4px',
        borderRadius: 4,
        wordBreak: 'break-word',
      }}
      {...props}
    />
  ),
  pre: (props) => (
    <pre
      style={{
        margin: '6px 0',
        padding: '8px 10px',
        background: 'var(--color-surface-subtle)',
        border: '1px solid var(--color-border)',
        borderRadius: 6,
        overflow: 'auto',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
      }}
      {...props}
    />
  ),
};

export default function Markdown({ children, style }) {
  return (
    <div style={style}>
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={COMPONENTS}>
        {children || ''}
      </ReactMarkdown>
    </div>
  );
}
