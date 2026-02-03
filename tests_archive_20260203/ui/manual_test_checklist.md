# UI Manual Test Checklist

## Prerequisites

- [ ] FastAPI backend running on http://localhost:8000
- [ ] Streamlit UI running on http://localhost:8501
- [ ] Test concept configuration loaded

## Session Management

### Create New Session
- [ ] Click "New Session" tab
- [ ] Select concept from dropdown
- [ ] Click "Start Interview" button
- [ ] Verify session created successfully
- [ ] Verify session ID displayed
- [ ] Verify opening question appears in chat

### Load Existing Session
- [ ] Click "Sessions" tab
- [ ] Verify session list loads
- [ ] Select a session from dropdown
- [ ] View session details in expander
- [ ] Click "Load" button
- [ ] Verify session loads correctly

### Delete Session
- [ ] Select a session
- [ ] Click "Delete" button
- [ ] Verify confirmation required (second click)
- [ ] Verify session removed from list

## Chat Interface

### Opening Question
- [ ] Opening question displayed when session loads
- [ ] Opening question in assistant message style

### Send Response
- [ ] Type message in chat input
- [ ] Press Enter or click send
- [ ] Verify message appears in chat (user style)
- [ ] Verify assistant response appears
- [ ] Verify turn counter increments

## Knowledge Graph

### Graph Display
- [ ] Navigate to "Knowledge Graph" tab
- [ ] Verify graph displays after first turn
- [ ] Verify nodes colored by type
- [ ] Verify edges connect nodes

### Graph Controls
- [ ] Select different layout algorithm
- [ ] Verify graph updates with new layout
- [ ] Toggle node labels on/off
- [ ] Filter by node type

## Metrics Panel

### Main Metrics
- [ ] Verify turn count displayed
- [ ] Verify turn progress bar shown
- [ ] Verify coverage percentage displayed
- [ ] Verify coverage visual bar shown

### Scoring Breakdown
- [ ] Verify gauge charts for each score
- [ ] Verify Coverage gauge works

### Strategy Display
- [ ] Verify current strategy shown
- [ ] Verify strategy description displayed

## Export

### Export JSON
- [ ] Select active session
- [ ] Go to "Export" tab
- [ ] Select "JSON" format
- [ ] Click "Export" button
- [ ] Verify download button appears

## End-to-End Interview Flow

### Complete Short Interview
- [ ] Create new session
- [ ] Respond to opening question
- [ ] Respond to 3-5 follow-up questions
- [ ] Verify knowledge graph builds
- [ ] Verify coverage increases
- [ ] Verify strategy changes appropriately
- [ ] Export session data
- [ ] Verify export contains all turns
