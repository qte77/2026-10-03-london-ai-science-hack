export function AppFooter({ commit, generatedAt }) {
  return (
    <footer className="app-footer">
      <p>
        Decision evidence from <strong>Parallax</strong> (GRAMSINATOR, Apache-2.0) · QC statistics
        from <strong>HackBench</strong>. Generated {generatedAt} · commit {commit}.
      </p>
    </footer>
  );
}
