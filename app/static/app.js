/* CineMatch v2.1 — browser UI; all recommendations are computed by the Python API. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const state = { liked:[], meta:null, movies:[], recommendations:[], offset:0, total:0,
                  search:'', genre:'', view:'explore', balance:65, serial:0, selectedId:null };
  const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  })[c]);
  let searchTimer, toastTimer;
  const posterLookups = new Map();
  // Image load/error events do not bubble. Listen in the capture phase.
  // When a historical CDN path fails, one server request fetches the latest
  // TMDB poster_path. The credential stays in the FastAPI environment.
  document.addEventListener('load', event => {
    if(event.target.matches?.('.poster-frame img')) event.target.classList.add('loaded');
  }, true);
  document.addEventListener('error', async event => {
    const img = event.target;
    if(!img.matches?.('.poster-frame img')) return;
    const id = Number(img.dataset.movieId);
    if(img.dataset.retried==='1' || !state.meta?.poster_refresh_enabled || !id) {
      img.remove();
      return;
    }
    img.dataset.retried='1';
    try {
      if(!posterLookups.has(id)) {
        posterLookups.set(id, api(`/api/poster/${id}`)
          .then(data=>data.poster_url)
          .catch(()=>null));
      }
      const replacement = await posterLookups.get(id);
      if(!img.isConnected) return;
      if(replacement && replacement !== img.src) {
        img.src = replacement;
      } else {
        img.remove();
      }
    } catch { img.remove(); }
  }, true);
  const palette = [
    ['#254567','#070e1d'],['#73413b','#15101b'],['#2d5b59','#0b1820'],
    ['#66518a','#15101d'],['#77614a','#14141d'],['#355767','#0b141c'],
    ['#754059','#1c1020'],['#556642','#121917']
  ];
  async function api(path, opts={}) {
    const response = await fetch(path, opts);
    let data;
    try { data = await response.json(); } catch { throw new Error('Invalid server response.'); }
    if(!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed.');
    return data;
  }
  function toast(message) { const element=$('toast');element.textContent=message;element.classList.add('active');
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>element.classList.remove('active'),3000); }
  const liked = id => state.liked.some(movie => movie.id===id);
  function poster(movie, extraClass='') {
    const color=palette[Math.abs(movie.id)%palette.length];
    const initial=movie.title.replace(/^(The|A|An)\s+/i,'').split(/\s+/).slice(0,2).map(x=>x[0]||'').join('').toUpperCase();
    const fallback = `<div class="poster-placeholder" style="--poster-a:${color[0]};--poster-b:${color[1]}"><div class="placeholder-symbol">✦</div><div class="placeholder-title">${escapeHTML(movie.title)}</div><div class="placeholder-year">${escapeHTML(movie.year || 'CINEMA')}</div></div>`;
    if(!movie.poster_url) return `<div class="poster-frame ${extraClass}">${fallback}</div>`;
    const link=escapeHTML(movie.poster_url);
    return `<div class="poster-frame ${extraClass}">${fallback}<img src="${link}" data-movie-id="${movie.id}" alt="${escapeHTML(movie.title)} movie poster" loading="lazy" decoding="async"></div>`;
  }
  function movieCard(movie, recommended=false, rank=0) {
    const selected=liked(movie.id);
    const badge=movie.catalog_rating!=null ? `<span class="score-badge"><span>★</span> ${Number(movie.catalog_rating).toFixed(1)}</span>` : '';
    const reason=recommended ? `<p class="card-reason">${escapeHTML(movie.reason || '')}</p>` : '';
    return `<article class="movie-card" data-id="${movie.id}">
      <button class="card-open" type="button" data-action="details" data-id="${movie.id}" aria-label="See details for ${escapeHTML(movie.title)}">
        ${poster(movie)}
        ${recommended?`<span class="ranking">#${rank} MATCH</span>`:''}
        ${badge}
        <span class="poster-more">View details <span aria-hidden="true">↗</span></span>
      </button>
      <button class="favorite-button ${selected?'selected':''}" data-action="toggle" data-id="${movie.id}" type="button" title="${selected?'Remove from':'Add to'} favorites" aria-label="${selected?'Remove':'Add'} ${escapeHTML(movie.title)} ${selected?'from':'to'} favorites">${selected?'✓':'+'}</button>
      <div class="card-text"><h3 title="${escapeHTML(movie.title)}">${escapeHTML(movie.title)}</h3><div class="card-meta"><span>${escapeHTML(movie.year ?? 'Film')}</span><span class="dot">·</span><span>${escapeHTML((movie.genres||[]).slice(0,2).join(' / ')||'Movie')}</span></div>${reason}</div>
    </article>`;
  }
  function empty(title, text) { return `<div class="empty-results"><span>✧</span><h3>${escapeHTML(title)}</h3><p>${escapeHTML(text)}</p></div>`; }
  function setView(which) {
    state.view=which;
    $('exploreView').hidden=which!=='explore'; $('recommendView').hidden=which!=='recommend';
    $('navExplore').classList.toggle('active',which==='explore');
    $('navForYou').classList.toggle('active',which==='recommend');
    $('workspace').scrollIntoView({behavior:'smooth',block:'start'});
    if(which==='recommend' && !state.recommendations.length) {
      $('recommendGrid').innerHTML=empty('Your recommendations start here', 'Choose a few favorites and click “Find my matches”.');
    }
  }
  function saved() {
    try {
      const raw=localStorage.getItem('cinematch-liked-v2');
      const v=JSON.parse(raw||'{}');
      if(v.source===state.meta.source && Array.isArray(v.ids))
        return [...new Set(v.ids.filter(Number.isInteger))].slice(0,8);
      // Preserve older browser favorites only if the old demo IDs still have meaning.
      if(!raw && state.meta.source==='demo') {
        const old=JSON.parse(localStorage.getItem('cinematch-liked')||'[]');
        if(Array.isArray(old))return [...new Set(old.filter(Number.isInteger))].slice(0,8);
      }
      return [];
    } catch { return []; }
  }
  function persist() {
    try { localStorage.setItem('cinematch-liked-v2',JSON.stringify({source:state.meta?.source,ids:state.liked.map(m=>m.id)})); } catch {}
  }
  function updateChoices() {
    $('tasteCount').textContent=`${state.liked.length} / 8`;
    $('navCount').textContent=String(state.liked.length);
    $('recommendBtn').disabled=!state.liked.length;
    $('selectedMovies').innerHTML=state.liked.length?state.liked.map(movie=>
      `<div class="chosen-row">${poster(movie,'mini-poster')}<span><strong>${escapeHTML(movie.title)}</strong><small>${escapeHTML(movie.year||'Film')}</small></span><button type="button" data-action="remove" data-id="${movie.id}" aria-label="Remove ${escapeHTML(movie.title)}" title="Remove">×</button></div>`).join('')
      : `<div class="empty-choices"><span>✧</span><strong>Nothing selected yet</strong><small>Choose a few movies to begin.</small></div>`;
    persist();
    document.querySelectorAll('.favorite-button').forEach(button=>{
      const active=liked(Number(button.dataset.id));button.classList.toggle('selected',active);
      button.textContent=active?'✓':'+'; button.setAttribute('aria-label',`${active?'Remove':'Add'} favorite`);
    });
    if(state.selectedId && $('dialogContent').querySelector('[data-action="toggle"]')) {
      const btn=$('dialogContent').querySelector('[data-action="toggle"]');
      btn.textContent=liked(state.selectedId)?'✓ Added to favorites':'+ Add to favorites';
    }
  }
  function toggle(movie) {
    if(!movie) return;
    if(liked(movie.id)) {state.liked=state.liked.filter(m=>m.id!==movie.id);toast('Removed from your favorites.');}
    else if(state.liked.length>=8) {toast('You can select up to 8 movies.');return;}
    else {state.liked.push(movie);toast('Added to your taste profile.');}
    updateChoices();
  }
  async function loadMovies(reset=false) {
    if(reset) {state.offset=0;state.movies=[];}
    const serial=++state.serial;
    $('resultsCount').textContent='Finding films…';
    if(reset) $('movieGrid').innerHTML='<div class="loading-message">Finding great movies…</div>';
    try {
      const params=new URLSearchParams({search:state.search,genre:state.genre,limit:'30',offset:String(state.offset)});
      const result=await api('/api/movies?'+params);
      if(serial!==state.serial) return;
      state.total=result.total;
      state.movies=reset?result.movies:[...state.movies,...result.movies];
      $('movieGrid').innerHTML=state.movies.length?state.movies.map(m=>movieCard(m)).join(''):
        empty('No matching movies','Try a different title or genre.');
      $('resultsCount').textContent=`${state.total.toLocaleString()} ${state.total===1?'film':'films'}`;
      $('loadMoreBtn').hidden=state.movies.length>=state.total;
    } catch(err) {if(serial!==state.serial)return;$('movieGrid').innerHTML=empty('Could not load movies',err.message);$('resultsCount').textContent='Offline';}
  }
  function updateBalance() {
    if(state.meta?.algorithm==='hybrid') {
      $('balanceInput').disabled=false;
      $('balanceValue').textContent=`${state.balance}% story / ${100-state.balance}% audience`;
      $('balanceHelp').textContent='Combines movie metadata with real MovieLens viewer patterns.';
    } else {
      $('balanceInput').disabled=true; $('balanceValue').textContent='Story & genres';
      $('balanceHelp').textContent='The current catalog uses content-based ML. Audience matching requires optional MovieLens ratings.';
    }
  }
  async function recommend() {
    if(!state.liked.length) return;
    setView('recommend');$('recommendGrid').innerHTML='<div class="loading-message">Finding your best matches…</div>';
    const button=$('recommendBtn');button.disabled=true;
    try {
      const data=await api('/api/recommend',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({liked_ids:state.liked.map(m=>m.id),limit:24,content_weight:state.balance/100})});
      state.recommendations=data.recommendations;
      $('recommendGrid').innerHTML=state.recommendations.length?
        state.recommendations.map((m,i)=>movieCard(m,true,i+1)).join(''):
        empty('No matches found','Try choosing some different movies.');
    } catch(err) {$('recommendGrid').innerHTML=empty('Could not recommend films',err.message);toast(err.message);}
    finally {button.disabled=!state.liked.length;}
  }
  function hero(movies) {
    if(movies.length<3)return;
    const choices=[movies[2],movies[0],movies[1]];
    $('heroPosters').innerHTML=choices.map((m,i)=>`<div class="hero-poster ${i===1?'poster-main':'poster-side'} ${i===0?'side-left':i===2?'side-right':''}">${poster(m)}<div class="hero-poster-caption">${escapeHTML(m.title)}</div></div>`).join('')+`<div class="hero-orbit">✦ CURATED FOR YOUR TASTE</div>`;
  }
  async function details(movieId) {
    const dialog=$('movieDialog');const content=$('dialogContent');
    state.selectedId=movieId;
    content.innerHTML='<div class="loading-message">Loading movie details…</div>';
    if(!dialog.open)dialog.showModal();
    try {
      const movie=await api('/api/movie/'+encodeURIComponent(movieId));
      if(state.selectedId!==movieId) return;
      content.innerHTML=`<div class="detail-layout"><div class="detail-poster">${poster(movie)}</div>
        <div class="detail-copy"><span class="section-kicker">MOVIE SPOTLIGHT</span><h2 id="dialogTitle">${escapeHTML(movie.title)}</h2>
        <div class="detail-stats"><span>${escapeHTML(movie.year??'')}</span>${movie.runtime?`<span>◷ ${movie.runtime} min</span>`:''}
          ${movie.catalog_rating!=null?`<span class="detail-rating">★ ${Number(movie.catalog_rating).toFixed(1)} / 10 <small>TMDB community</small></span>`:''}</div>
        <div class="detail-genres">${movie.genres.map(g=>`<span>${escapeHTML(g)}</span>`).join('')}</div>
        ${movie.tagline?`<p class="detail-tagline">“${escapeHTML(movie.tagline)}”</p>`:''}
        <p class="detail-description">${escapeHTML(movie.overview||'A story waiting to be discovered. Full plot information is not available for this film.')}</p>
        <div class="detail-actions"><button type="button" class="button-primary" data-action="toggle" data-id="${movie.id}">${liked(movie.id)?'✓ Added to favorites':'+ Add to favorites'}</button>
          ${movie.tmdb_url?`<a class="button-secondary" href="${escapeHTML(movie.tmdb_url)}" target="_blank" rel="noopener noreferrer">View on TMDB ↗</a>`:''}</div></div></div>
        ${movie.similar?.length?`<div class="also-like"><h3>More like this <span>→</span></h3><div class="mini-grid">${movie.similar.slice(0,5).map(m=>`<button type="button" class="mini-card" data-action="details" data-id="${m.id}">${poster(m)}<strong>${escapeHTML(m.title)}</strong></button>`).join('')}</div></div>`:''}`;
    }catch(err){content.innerHTML=empty('Unable to load details',err.message);}
  }
  async function useExamples() {
    const names=['Inception','Interstellar','Arrival'];const chosen=[];
    for(const title of names){const res=await api(`/api/movies?search=${encodeURIComponent(title)}&limit=12`);
      const m=res.movies.find(m=>m.title.toLowerCase()===title.toLowerCase());if(m)chosen.push(m);}
    if(!chosen.length){toast('Could not find example titles in this catalog.');return;}
    state.liked=chosen;updateChoices();toast('Added some science-fiction favorites.');
  }
  function action(event) {
    const element=event.target.closest('[data-action]');if(!element)return;
    const id=Number(element.dataset.id),type=element.dataset.action;
    if(type==='details') {details(id);return;}
    if(type==='remove') {state.liked=state.liked.filter(m=>m.id!==id);updateChoices();return;}
    const movie=[...state.liked,...state.movies,...state.recommendations].find(m=>m.id===id);
    if(movie)toggle(movie);
    else api('/api/movie/'+id).then(toggle).catch(err=>toast(err.message));
  }
  async function init() {
    $('movieGrid').addEventListener('click',action);
    $('recommendGrid').addEventListener('click',action);
    $('selectedMovies').addEventListener('click',action);
    $('dialogContent').addEventListener('click',action);
    $('movieDialog').addEventListener('click',event=>{if(event.target===$('movieDialog'))$('movieDialog').close();});
    $('dialogClose').addEventListener('click',()=>$('movieDialog').close());
    $('movieDialog').addEventListener('close',()=>{state.selectedId=null;});
    $('searchInput').addEventListener('input',event=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{state.search=event.target.value;loadMovies(true);},230);});
    $('genreSelect').addEventListener('change',event=>{state.genre=event.target.value;syncQuick();loadMovies(true);});
    $('quickFilters').addEventListener('click',event=>{
      const button=event.target.closest('[data-genre]');if(!button)return;
      state.genre=button.dataset.genre;$('genreSelect').value=state.genre;syncQuick();loadMovies(true);
    });
    $('loadMoreBtn').addEventListener('click',()=>{state.offset=state.movies.length;loadMovies(false);});
    $('recommendBtn').addEventListener('click',recommend);
    $('heroStart').addEventListener('click',()=>{$('workspace').scrollIntoView({behavior:'smooth'});setTimeout(()=>$('searchInput').focus({preventScroll:true}),220);});
    $('exampleBtn').addEventListener('click',()=>useExamples().catch(err=>toast(err.message)));
    $('clearBtn').addEventListener('click',()=>{state.liked=[];updateChoices();toast('Your list is clear.');});
    $('navExplore').addEventListener('click',()=>setView('explore'));
    $('navForYou').addEventListener('click',()=>setView('recommend'));
    $('editTasteBtn').addEventListener('click',()=>setView('explore'));
    $('balanceInput').addEventListener('input',event=>{state.balance=Number(event.target.value);updateBalance();});
    try {
      state.meta=await api('/api/meta');
      const count=state.meta.movie_count.toLocaleString();
      const mode=state.meta.source==='catalog'?'EXPANDED CATALOG':state.meta.source==='movielens'?'MOVIELENS':'DEMO LIBRARY';
      $('datasetLabel').textContent=`${mode} · ${count} films`;
      $('heroMovieCount').textContent=count;
      $('footerSource').textContent=state.meta.source==='catalog'
        ?`${count} titles · historic metadata (up to 2017)`
        :state.meta.source==='movielens'?`${count} titles · historical MovieLens ratings`:`${count} curated titles · small offline demo`;
      $('genreSelect').innerHTML='<option value="">All genres</option>'+state.meta.genres.map(g=>`<option value="${escapeHTML(g)}">${escapeHTML(g)}</option>`).join('');
      const candidates=['Action','Comedy','Drama','Sci-Fi','Science Fiction','Thriller','Romance','Animation'];
      const genres=candidates.filter(g=>state.meta.genres.includes(g)).slice(0,6);
      $('quickFilters').innerHTML=`<button type="button" class="quick-chip active" data-genre="">All movies</button>`+
        genres.map(g=>`<button type="button" class="quick-chip" data-genre="${escapeHTML(g)}">${escapeHTML(g)}</button>`).join('');
      updateBalance();
      const ids=saved();
      const cached=await Promise.all(ids.map(id=>api('/api/movie/'+id).catch(()=>null)));
      state.liked=cached.filter(Boolean);updateChoices();await loadMovies(true);
      hero(state.movies);
    } catch(err) {
      $('datasetLabel').textContent='SERVER UNAVAILABLE';
      $('movieGrid').innerHTML=empty('Cannot reach CineMatch',err.message);
      toast('Could not load the movie catalog.');
    }
  }
  function syncQuick() {document.querySelectorAll('.quick-chip').forEach(el=>el.classList.toggle('active',el.dataset.genre===state.genre));}
  init();
})();
