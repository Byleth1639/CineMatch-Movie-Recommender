/* CineMatch interface: all recommendations are computed on the Python server. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const state = { liked: [], meta: null, view: 'explore', search: '', genre: '', offset: 0,
                  total: 0, movies: [], recommendations: [], fetchSerial: 0, balance: 65 };
  const PALETTES = [
    ['#8052b9','#302653','#121528'],['#cc6979','#783c81','#222044'],
    ['#478ca9','#30507f','#152544'],['#8e945e','#5b5587','#232744'],
    ['#bd935e','#98546c','#292447'],['#907fc9','#574d94','#242147'],
    ['#6fa3a4','#54738b','#26294e'],['#c97872','#8e536b','#2a2c52'],
    ['#b68dbf','#775792','#282143'],['#6d8cbc','#464d94','#272244'],
    ['#b879a1','#6d4975','#25204b'],['#6d9b78','#3e6c76','#1e2c4a']
  ];
  const escapeHTML = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
  let debounceTimer, toastTimer;

  function getStored() {
    try { const saved = JSON.parse(localStorage.getItem('cinematch-liked') || '[]');
      return Array.isArray(saved) ? [...new Set(saved.filter(Number.isInteger))].slice(0,8) : [];
    } catch { return []; }
  }
  function persist() {
    try { localStorage.setItem('cinematch-liked', JSON.stringify(state.liked.map(m => m.id))); }
    catch { /* private browsing can block storage */ }
  }
  async function api(path, options) {
    const response = await fetch(path, options);
    let data;
    try { data = await response.json(); } catch { throw new Error('Server sent an invalid response.'); }
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed.');
    return data;
  }
  function notify(message) {
    const el = $('toast'); el.textContent = message; el.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 2800);
  }
  function isLiked(id) { return state.liked.some(m => m.id === id); }
  function truncate(s, n) { return s.length > n ? s.slice(0, n-1) + '…' : s; }
  function posterMarkup(movie) {
    const p = PALETTES[Math.abs(movie.id) % PALETTES.length];
    const bg = `radial-gradient(ellipse at 35% 20%, ${p[0]}, ${p[1]} 54%, ${p[2]} 100%)`;
    const initials = movie.title.replace(/^(The|A|An)\s+/i,'').split(/\s+/).slice(0,2).map(x=>x[0]||'').join('').toUpperCase();
    return `<div class="poster" style="background:${bg}">
       <span class="poster-year">${escapeHTML(movie.year ?? 'FILM')}</span>
       <span class="poster-mark" aria-hidden="true">${escapeHTML(initials)}</span>
       <span class="poster-genre">${escapeHTML(movie.genres.slice(0,2).join(' · ') || 'Cinema')}</span>
       </div>`;
  }
  function movieCard(movie, isRecommended=false, rank=0) {
    const chosen = isLiked(movie.id);
    const action = chosen ? 'Remove from favorites' : 'Add to favorites';
    const rating = movie.average_rating != null
      ? `<div class="movie-rating">★ ${Number(movie.average_rating).toFixed(1)} <span>· ${movie.rating_count.toLocaleString()} ratings</span></div>` : '';
    return `<article class="movie-card" data-id="${movie.id}">
        ${isRecommended ? `<span class="rank-pill">#${rank} for you</span>` : ''}
        ${posterMarkup(movie)}
        <button type="button" class="add-button ${chosen?'chosen':''}" data-action="toggle"
          data-id="${movie.id}" aria-label="${action}: ${escapeHTML(movie.title)}" aria-pressed="${chosen}">${chosen?'✓':'+'}</button>
        <div class="movie-info"><h3 class="movie-title" title="${escapeHTML(movie.title)}">${escapeHTML(movie.title)}</h3>
        <div class="movie-sub">${escapeHTML(movie.genres.slice(0,2).join(' · ') || 'Movie')}</div>
        ${rating}${isRecommended ? `<p class="movie-reason">✧ ${escapeHTML(movie.reason)}</p>` : ''}
        </div></article>`;
  }
  function emptyContent(heading, message) {
    return `<div class="empty-results"><span class="empty-icon">✧</span><strong>${escapeHTML(heading)}</strong><p>${escapeHTML(message)}</p></div>`;
  }
  function updateSelected() {
    $('tasteCount').textContent = `${state.liked.length} / 8`;
    $('navCount').textContent = String(state.liked.length);
    $('recommendBtn').disabled = state.liked.length === 0;
    $('clearBtn').disabled = state.liked.length === 0;
    $('selectedMovies').innerHTML = state.liked.length ? state.liked.map(m =>
      `<span class="selected-chip">${escapeHTML(truncate(m.title,28))}<button type="button" data-action="remove" data-id="${m.id}" aria-label="Remove ${escapeHTML(m.title)}">×</button></span>`
    ).join('') : '<div class="empty-taste"><span class="empty-orbit">✧</span><strong>Your taste starts here</strong><small>Add a few favorites from the movie library.</small></div>';
    document.querySelectorAll('.add-button').forEach(btn => {
      const id = Number(btn.dataset.id); const chosen = isLiked(id);
      btn.classList.toggle('chosen',chosen); btn.textContent=chosen?'✓':'+';
      btn.setAttribute('aria-pressed',String(chosen));
      const title = btn.closest('.movie-card')?.querySelector('.movie-title')?.textContent || 'movie';
      btn.setAttribute('aria-label',`${chosen?'Remove from':'Add to'} favorites: ${title}`);
    });
    persist();
  }
  function toggleMovie(movie) {
    if (!movie) return;
    if (isLiked(movie.id)) state.liked = state.liked.filter(m => m.id !== movie.id);
    else if (state.liked.length >= 8) { notify('Choose up to 8 favorite movies.'); return; }
    else state.liked.push(movie);
    updateSelected();
    if (state.view === 'recommend') {
      // Never show stale recommendations after the chosen films change.
      $('recommendGrid').innerHTML = emptyContent('Your picks changed', 'Click Find my movies to refresh your recommendations.');
    }
  }
  function setView(view) {
    state.view=view;
    $('exploreView').hidden=view!=='explore';$('recommendView').hidden=view!=='recommend';
    $('navExplore').classList.toggle('active',view==='explore');
    $('navForYou').classList.toggle('active',view==='recommend');
    $('workspace').scrollIntoView({behavior:'smooth',block:'start'});
    if (view==='recommend' && state.recommendations.length===0 && !$('recommendGrid').innerHTML)
      $('recommendGrid').innerHTML = emptyContent('Your perfect watchlist starts with you','Choose your favorite movies and click Find my movies.');
  }
  function updateStyleLabels() {
    $('balanceValue').textContent = `${state.balance}% genre / ${100-state.balance}% audience`;
    $('balanceInput').value=String(state.balance);
    if (state.meta?.algorithm==='content-based') {
      $('balanceValue').textContent='100% genre';
      $('balanceInput').disabled=true;
      $('balanceHelp').textContent='Demo mode uses genre and release-decade similarities. Download MovieLens data to unlock audience-based filtering.';
    }
  }
  async function loadMovies(reset=true) {
    if (reset) { state.offset=0; state.movies=[]; }
    const serial=++state.fetchSerial;
    $('movieGrid').innerHTML = state.offset===0 ? emptyContent('Finding films…','Searching your movie library.') : $('movieGrid').innerHTML;
    const query=new URLSearchParams({search:state.search,genre:state.genre,limit:'36',offset:String(state.offset)});
    try {
      const data=await api(`/api/movies?${query}`);
      if (serial!==state.fetchSerial) return;
      state.total=data.total;state.movies=state.movies.concat(data.movies);
      $('resultsCount').textContent = `${data.total.toLocaleString()} ${data.total===1?'movie':'movies'}`;
      $('movieGrid').innerHTML=state.movies.length ? state.movies.map(m=>movieCard(m)).join('') : emptyContent('No matches found','Try a different title or genre.');
      $('loadMoreBtn').hidden=state.movies.length>=state.total;
    } catch(err) {
      if(serial!==state.fetchSerial) return;
      $('movieGrid').innerHTML=emptyContent('Could not load movies',err.message);
      notify(err.message);
    }
  }
  async function recommend() {
    if (!state.liked.length) { notify('Pick at least one movie you love first.'); setView('explore'); return; }
    const button=$('recommendBtn');button.disabled=true;
    $('recommendGrid').innerHTML=emptyContent('Finding your next favorite…','Comparing your picks with the movie collection.');
    setView('recommend');
    const likedIds=state.liked.map(m=>m.id);
    try {
      const data=await api('/api/recommend',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({liked_ids:likedIds,content_weight:state.balance/100,limit:12})});
      if (JSON.stringify(likedIds)!==JSON.stringify(state.liked.map(m=>m.id))) return;
      state.recommendations=data.recommendations;
      $('recommendGrid').innerHTML=data.recommendations.length ? data.recommendations.map((m,i)=>movieCard(m,true,i+1)).join('') : emptyContent('No recommendations yet','Try a different set of movies.');
    } catch(err) { $('recommendGrid').innerHTML=emptyContent('Recommendations unavailable',err.message);notify(err.message); }
    finally { button.disabled=state.liked.length===0; }
  }
  async function useExamples() {
    const names=['Inception','Interstellar','Arrival'];const found=[];
    for (const name of names) {
      const data=await api(`/api/movies?search=${encodeURIComponent(name)}&limit=10`);
      const first=data.movies.find(m=>m.title.toLowerCase()===name.toLowerCase());
      if (first) found.push(first);
    }
    state.liked=found; updateSelected();notify('Added 3 science fiction favorites.');
  }
  function handleToggles(event) {
    const btn=event.target.closest('button[data-action]'); if(!btn) return;
    const id=Number(btn.dataset.id);
    if(btn.dataset.action==='remove') {state.liked=state.liked.filter(m=>m.id!==id);updateSelected();return;}
    const movie=[...state.movies,...state.recommendations,...state.liked].find(m=>m.id===id);
    toggleMovie(movie);
  }
  async function init() {
    const savedIds=getStored();
    $('selectedMovies').addEventListener('click',handleToggles);
    $('movieGrid').addEventListener('click',handleToggles);
    $('recommendGrid').addEventListener('click',handleToggles);
    $('searchInput').addEventListener('input',e=>{clearTimeout(debounceTimer);debounceTimer=setTimeout(()=>{state.search=e.target.value;loadMovies(true);},260);});
    $('genreSelect').addEventListener('change',e=>{state.genre=e.target.value;loadMovies(true);});
    $('loadMoreBtn').addEventListener('click',()=>{state.offset=state.movies.length;loadMovies(false);});
    $('recommendBtn').addEventListener('click',recommend);
    $('heroStart').addEventListener('click',()=>{$('workspace').scrollIntoView({behavior:'smooth',block:'start'});$('searchInput').focus({preventScroll:true});});
    $('exampleBtn').addEventListener('click',()=>useExamples().catch(err=>notify(err.message)));
    $('clearBtn').addEventListener('click',()=>{state.liked=[];updateSelected();notify('Your favorites have been cleared.');});
    $('navExplore').addEventListener('click',()=>setView('explore'));
    $('navForYou').addEventListener('click',()=>setView('recommend'));
    $('editTasteBtn').addEventListener('click',()=>setView('explore'));
    $('balanceInput').addEventListener('input',e=>{state.balance=Number(e.target.value);updateStyleLabels();});
    try {
      state.meta=await api('/api/meta');
      const label=state.meta.source==='movielens'?'MOVIELENS LIVE':'OFFLINE DEMO';
      $('datasetLabel').textContent=`${label} · ${state.meta.movie_count.toLocaleString()} films`;
      $('footerSource').textContent=state.meta.source==='movielens'
        ? `MovieLens dataset · ${state.meta.ratings_count.toLocaleString()} real ratings` : '257 curated movie titles · Demo has no user ratings';
      $('genreSelect').innerHTML='<option value="">All genres</option>'+state.meta.genres
        .map(g=>`<option value="${escapeHTML(g)}">${escapeHTML(g)}</option>`).join('');
      updateStyleLabels();
      if (savedIds.length) {
        const matches = await Promise.all(savedIds.map(id =>
          api(`/api/movie/${id}`).catch(() => null)));
        state.liked = matches.filter(Boolean);
      }
      updateSelected(); await loadMovies(true);
    }catch(err){
      $('datasetLabel').textContent='SERVER UNAVAILABLE';
      $('movieGrid').innerHTML=emptyContent('Could not connect to server',err.message);
      notify('Check that the Python server is running.');
    }
  }
  init();
})();
