/* Betriebsstatus Widget – Kleine Scheidegg
 * Embed: <div data-bss="kleine-scheidegg"></div>
 *        <script src="https://tsolenthaler.github.io/jrtag-betriebsstatus/js/kleine-scheidegg/widget.js" defer></script>
 * Or use the universal loader:
 *        <div class="bss-widget" data-bss-tenant="kleine-scheidegg" data-bss-base="https://tsolenthaler.github.io/jrtag-betriebsstatus"></div>
 *        <script src="https://tsolenthaler.github.io/jrtag-betriebsstatus/js/widget.js" defer></script>
 */
(function () {
  'use strict';

  var API_URL = 'https://tsolenthaler.github.io/jrtag-betriebsstatus/api/kleine-scheidegg/feed.json';
  var DETAIL_URL = 'https://tsolenthaler.github.io/jrtag-betriebsstatus/operating-status/kleine-scheidegg/';
  var CSS_ID = 'bss-style-kleine_scheidegg';

  var STATUS_COLOR = {
    open:'#16a34a', closed:'#dc2626', preparation:'#d97706',
    free:'#2563eb', full:'#7c3aed', disabled:'#6b7280', unknown:'#9ca3af'
  };
  var STATUS_LABEL_DE = {
    open:'offen', closed:'geschlossen', preparation:'in Vorbereitung',
    free:'frei', full:'voll', disabled:'deaktiviert', unknown:'unbekannt'
  };

  function injectStyles() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent = [
      '.bss-widget{font-family:system-ui,sans-serif;max-width:480px;border:1px solid #e2e8f0;',
      'border-radius:.5rem;overflow:hidden;background:#fff;font-size:.875rem;}',
      '.bss-hdr{background:#1e3a5f;color:#fff;padding:.6rem .9rem;}',
      '.bss-hdr h3{margin:0;font-size:1rem;font-weight:600;}',
      '.bss-hdr p{margin:.15rem 0 0;font-size:.72rem;opacity:.7;}',
      '.bss-sec h4{margin:0;padding:.4rem .8rem;background:#f1f5f9;',
      'border-bottom:1px solid #e2e8f0;font-size:.78rem;font-weight:600;color:#475569;}',
      '.bss-list{list-style:none;margin:0;padding:0;}',
      '.bss-list li{display:flex;align-items:center;gap:.5rem;padding:.4rem .8rem;',
      'border-bottom:1px solid #f1f5f9;}',
      '.bss-list li:last-child{border-bottom:none;}',
      '.bss-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}',
      '.bss-name{flex:1;color:#1e293b;}',
      '.bss-state{font-size:.72rem;color:#64748b;white-space:nowrap;}',
      '.bss-footer{padding:.4rem .8rem;font-size:.7rem;color:#94a3b8;border-top:1px solid #e2e8f0;}',
      '.bss-error{padding:.75rem;color:#dc2626;font-size:.8rem;}'
    ].join('');
    (document.head || document.documentElement).appendChild(s);
  }

  function esc(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function formatDateTimeDe(value) {
    if (!value) return '';
    var date = new Date(value);
    if (isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat('de-DE', {
      day:'2-digit', month:'2-digit', year:'numeric',
      hour:'2-digit', minute:'2-digit', hour12:false
    }).format(date).replace(',', '').trim();
  }

  function groupBy(items, key) {
    return items.reduce(function(acc, item) {
      (acc[item[key]] = acc[item[key]] || []).push(item);
      return acc;
    }, {});
  }

  function renderItems(items, container) {
    var groups = groupBy(items, '_tags');
    var order = ['Anlage', 'Piste', 'Trail', 'Gastro'];
    var html = '';
    order.forEach(function(tag) {
      var grp = groups[tag];
      if (!grp || !grp.length) return;
      var open = grp.filter(function(i) { return i._stateRaw === 'open'; }).length;
      html += '<div class="bss-sec"><h4>' + esc(tag) +
              ' <span style="font-weight:400;color:#94a3b8">(' + open + '/' + grp.length + ' offen)</span></h4>' +
              '<ul class="bss-list">';
      grp.forEach(function(item) {
        var color = STATUS_COLOR[item._stateRaw] || STATUS_COLOR.unknown;
        var label = STATUS_LABEL_DE[item._stateRaw] || item._stateRaw;
        html += '<li>' +
                '<span class="bss-dot" style="background:' + color + '"></span>' +
                '<span class="bss-name">' + esc(item.title) + '</span>' +
                '<span class="bss-state">' + esc(label) + '</span>' +
                '</li>';
      });
      html += '</ul></div>';
    });
    container.innerHTML = html;
  }

  function init() {
    injectStyles();
    var targets = document.querySelectorAll('[data-bss="kleine-scheidegg"]');
    for (var i = 0; i < targets.length; i++) {
      var el = targets[i];
      el.className = (el.className + ' bss-widget').trim();
      (function(elem) {
        fetch(API_URL)
          .then(function(r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
          })
          .then(function(data) {
            var updated = (data.items && data.items[0] && data.items[0].date_published) || '';
            var d = updated ? formatDateTimeDe(updated) : '';
            var hdr = document.createElement('div');
            hdr.className = 'bss-hdr';
            hdr.innerHTML = '<h3>' + esc(data.title || 'Kleine Scheidegg') + '</h3>' +
                            (d ? '<p>Stand: ' + esc(d) + '</p>' : '');
            elem.appendChild(hdr);
            var body = document.createElement('div');
            renderItems(data.items || [], body);
            elem.appendChild(body);
            var footer = document.createElement('div');
            footer.className = 'bss-footer';
            footer.innerHTML = 'Daten: Siscontrol SISMedia &bull; ' +
              '<a href="' + esc(DETAIL_URL) + '" style="color:inherit">Details</a>';
            elem.appendChild(footer);
          })
          .catch(function(err) {
            elem.innerHTML = '<p class="bss-error">Status konnte nicht geladen werden.</p>';
            console.warn('BSS widget error:', err);
          });
      }(el));
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());


