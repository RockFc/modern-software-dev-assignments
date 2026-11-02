async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

const notesState = { page: 1, pageSize: 5, q: '', sort: 'created_desc', total: 0 };
const actionsState = { page: 1, pageSize: 5, total: 0 };

function totalPages(total, pageSize) {
  return Math.max(1, Math.ceil((total || 0) / pageSize));
}

async function loadNotes() {
  const list = document.getElementById('notes');
  const meta = document.getElementById('notes-meta');
  const pageLabel = document.getElementById('notes-page-label');
  list.innerHTML = '';

  let url;
  if (notesState.q) {
    const params = new URLSearchParams({
      q: notesState.q,
      page: String(notesState.page),
      page_size: String(notesState.pageSize),
      sort: notesState.sort,
    });
    url = `/notes/search?${params.toString()}`;
  } else {
    const params = new URLSearchParams({
      page: String(notesState.page),
      page_size: String(notesState.pageSize),
    });
    url = `/notes/?${params.toString()}`;
  }

  const body = await fetchJSON(url);
  notesState.total = body.total;
  notesState.page = body.page;
  notesState.pageSize = body.page_size;

  for (const n of body.items) {
    const li = document.createElement('li');
    li.textContent = `${n.title}: ${n.content}`;
    list.appendChild(li);
  }

  const pages = totalPages(body.total, body.page_size);
  meta.textContent = notesState.q
    ? `Search "${notesState.q}": ${body.total} result(s)`
    : `${body.total} note(s)`;
  pageLabel.textContent = `Page ${body.page} / ${pages}`;
  document.getElementById('notes-prev').disabled = body.page <= 1;
  document.getElementById('notes-next').disabled = body.page >= pages;
}

async function loadActions() {
  const list = document.getElementById('actions');
  const meta = document.getElementById('actions-meta');
  const pageLabel = document.getElementById('actions-page-label');
  list.innerHTML = '';

  const params = new URLSearchParams({
    page: String(actionsState.page),
    page_size: String(actionsState.pageSize),
  });
  const body = await fetchJSON(`/action-items/?${params.toString()}`);
  actionsState.total = body.total;
  actionsState.page = body.page;
  actionsState.pageSize = body.page_size;

  for (const a of body.items) {
    const li = document.createElement('li');
    li.textContent = `${a.description} [${a.completed ? 'done' : 'open'}]`;
    if (!a.completed) {
      const btn = document.createElement('button');
      btn.textContent = 'Complete';
      btn.onclick = async () => {
        await fetchJSON(`/action-items/${a.id}/complete`, { method: 'PUT' });
        loadActions();
      };
      li.appendChild(btn);
    }
    list.appendChild(li);
  }

  const pages = totalPages(body.total, body.page_size);
  meta.textContent = `${body.total} action item(s)`;
  pageLabel.textContent = `Page ${body.page} / ${pages}`;
  document.getElementById('actions-prev').disabled = body.page <= 1;
  document.getElementById('actions-next').disabled = body.page >= pages;
}

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('note-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('note-title').value;
    const content = document.getElementById('note-content').value;
    await fetchJSON('/notes/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content }),
    });
    e.target.reset();
    notesState.page = 1;
    loadNotes();
  });

  document.getElementById('action-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const description = document.getElementById('action-desc').value;
    await fetchJSON('/action-items/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description }),
    });
    e.target.reset();
    actionsState.page = 1;
    loadActions();
  });

  document.getElementById('note-search-btn').addEventListener('click', () => {
    notesState.q = document.getElementById('note-search').value.trim();
    notesState.sort = document.getElementById('note-sort').value;
    notesState.page = 1;
    loadNotes();
  });

  document.getElementById('note-clear-search').addEventListener('click', () => {
    document.getElementById('note-search').value = '';
    notesState.q = '';
    notesState.page = 1;
    loadNotes();
  });

  document.getElementById('note-sort').addEventListener('change', () => {
    notesState.sort = document.getElementById('note-sort').value;
    if (notesState.q) {
      notesState.page = 1;
      loadNotes();
    }
  });

  document.getElementById('notes-prev').addEventListener('click', () => {
    if (notesState.page > 1) {
      notesState.page -= 1;
      loadNotes();
    }
  });
  document.getElementById('notes-next').addEventListener('click', () => {
    notesState.page += 1;
    loadNotes();
  });

  document.getElementById('actions-prev').addEventListener('click', () => {
    if (actionsState.page > 1) {
      actionsState.page -= 1;
      loadActions();
    }
  });
  document.getElementById('actions-next').addEventListener('click', () => {
    actionsState.page += 1;
    loadActions();
  });

  loadNotes();
  loadActions();
});