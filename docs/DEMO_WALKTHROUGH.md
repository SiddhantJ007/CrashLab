# Demo Walkthrough

Use this walkthrough for recruiter demos, project reviews, or portfolio conversations.

## Recommended Demo Narrative
CrashLab is a target-aware AI workflow evaluation platform. Instead of manually prompting one workflow at a time, it runs reusable, family-specific tests, scores observable behavior, assigns trust labels, and stores/export results.

## Suggested Demo Steps
1. Open the live dashboard.
   - Live URL: `https://crashlab.onrender.com`
   - Loom walkthrough: `https://www.loom.com/share/1a6fc484dc93431f801e0e6d47d5a446`
2. Show the two built-in public target types.
   - Flowise
   - Dify
3. Open `Preview Suite` for one target.
   - Explain that suite choice depends on the target family.
4. Run a target.
   - Show live run logs and progress.
5. Open recent runs.
   - Explain trust labels and why not every run gets a normal benchmark score.
6. Open compare latest results.
   - Show latest cross-target risk signals.
7. Export a report.
   - Markdown, JSON, or CSV
8. Open Add Target.
   - Explain dynamic onboarding and the intelligence-assisted plan suggestion path.

## Talking Points
- Flowise represents orchestration-style workflows.
- Dify represents structured retrieval/assistant workflows.
- CrashLab does not assume one scoring rubric fits every workflow family.
- Supabase persistence keeps the public Render demo from losing run history after restarts.

## Demo Media
[![CrashLab Loom Demo](assets/loom-preview.png)](https://www.loom.com/share/1a6fc484dc93431f801e0e6d47d5a446)

The Loom recording is the primary walkthrough asset. It already shows the main dashboard, so the supporting screenshots focus on deeper product interactions rather than duplicating the same hero view.

## Supporting Screenshots
<table>
  <tr>
    <td width="50%" align="center">
      <a href="assets/suite-preview.png"><img src="assets/suite-preview.png" alt="CrashLab suite preview" width="100%"/></a><br/>
      <strong>Suite Preview</strong>
    </td>
    <td width="50%" align="center">
      <a href="assets/custom-target.png"><img src="assets/custom-target.png" alt="CrashLab add target form" width="100%"/></a><br/>
      <strong>Add Target</strong>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <a href="assets/live-run.png"><img src="assets/live-run.png" alt="CrashLab live run log" width="100%"/></a><br/>
      <strong>Live Run</strong>
    </td>
    <td width="50%" align="center">
      <a href="assets/report-export.png"><img src="assets/report-export.png" alt="CrashLab report export and recent runs" width="100%"/></a><br/>
      <strong>Report Export</strong>
    </td>
  </tr>
</table>
