// Digital Court 品牌首頁與產品頁共用：洽詢表單送到 /platform/api/leads、首頁產品分類篩選、手機選單
(function () {
  document.querySelectorAll('form.lead-form').forEach(function (form) {
    var msg = form.querySelector('.form-msg')
    var show = function (text, ok) { msg.textContent = text; msg.className = 'form-msg ' + (ok ? 'ok' : 'bad'); msg.hidden = false }
    form.addEventListener('submit', function (e) {
      e.preventDefault()
      var f = new FormData(form)
      var products = f.getAll('products')
      var area = String(f.get('area') || '').trim(), qty = String(f.get('qty') || '')
      var needs = []
      if (area) needs.push('地區：' + area)
      if (qty) needs.push('台數：' + qty)
      needs = needs.concat(products, f.getAll('needs'))
      var topic = form.dataset.topic || (products.length === 1 ? products[0] : '產品洽詢')
      var body = { topic: topic, page: location.pathname, name: f.get('name'), contact: f.get('contact'), org: f.get('org'),
        size: f.get('size'), message: f.get('message'), website: f.get('website'), needs: needs }
      if (!String(body.name || '').trim() || !String(body.contact || '').trim()) return show('請填寫稱呼與聯絡方式', false)
      var btn = form.querySelector('button[type=submit]')
      btn.disabled = true; btn.textContent = '送出中…'
      fetch('/platform/api/leads', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d } }) })
        .then(function (x) {
          if (!x.ok) throw new Error((x.d && (x.d.error || x.d.detail)) || '送出失敗，請稍後再試')
          form.reset(); show('已收到！我們會盡快用你留的聯絡方式與你聯絡。', true)
        })
        .catch(function (err) { show(err.message || '送出失敗，請稍後再試', false) })
        .finally(function () { btn.disabled = false; btn.textContent = '送出' })
    })
  })

  // 首頁產品分類
  var chips = document.querySelectorAll('.chips button')
  chips.forEach(function (b) {
    b.addEventListener('click', function () {
      chips.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)) })
      var c = b.dataset.cat
      document.querySelectorAll('#products .pcard').forEach(function (card) {
        card.classList.toggle('hide', c !== 'all' && (' ' + card.dataset.cats + ' ').indexOf(' ' + c + ' ') < 0)
      })
    })
  })

  // 手機選單：點了連結就收起來
  document.querySelectorAll('.menu nav a').forEach(function (a) {
    a.addEventListener('click', function () { a.closest('details').open = false })
  })
})()
