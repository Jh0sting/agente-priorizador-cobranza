(() => {
  "use strict";

  const PASO = 20;
  const COLOR_TRAMO = {
    preventiva: "var(--t-preventiva)",
    temprana: "var(--t-temprana)",
    intermedia: "var(--t-intermedia)",
    "tardía": "var(--t-tardia)",
    prejudicial: "var(--t-prejudicial)",
  };

  const $ = (sel) => document.querySelector(sel);
  const soles = (n, dec = 0) =>
    "S/ " + Number(n).toLocaleString("es-PE", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const compacto = (n) =>
    n >= 1e6 ? "S/ " + (n / 1e6).toLocaleString("es-PE", { maximumFractionDigits: 2 }) + " M"
    : n >= 1e3 ? "S/ " + (n / 1e3).toLocaleString("es-PE", { maximumFractionDigits: 0 }) + " mil"
    : soles(n);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const primerNombre = (cliente) => cliente.split(" ")[0];

  let datos = null;
  let visibles = PASO;
  const filtro = { texto: "", tramo: "", distrito: "", producto: "" };

  // ---------- Mensajes (plantillas deterministas) ----------
  // En el agente de IA, redactor_mensajes los personaliza con Gemini.
  function mensajePara(c) {
    const nombre = primerNombre(c.cliente);
    const cuota = soles(c.cuota_mensual, 2);
    const firma = "Área de Recuperaciones";
    const canal = c.canal_sugerido;

    if (canal === "Llamada") {
      const propuesta = {
        preventiva: `recordarle que su próxima cuota de ${cuota} vence pronto y resolver cualquier duda.`,
        temprana: `conversar sobre su cuota pendiente de ${cuota} y acordar juntos una fecha de pago que le sea posible.`,
        intermedia: `contarle que podemos reprogramar sus cuotas para que le sea más fácil ponerse al día.`,
        "tardía": `buscar juntos un acuerdo de pago que se ajuste a su situación actual.`,
        prejudicial: `ofrecerle una última alternativa de acuerdo antes de otras gestiones.`,
      }[c.tramo];
      return [
        `1. Saludo: "Buenos días, ¿hablo con ${nombre}? Le saluda el ${firma}."`,
        `2. Motivo: "Le llamo por su ${c.producto.toLowerCase()} (${c.id_credito}); queremos ${propuesta}"`,
        `3. Escuchar: preguntar con respeto la causa del atraso y registrarla.`,
        `4. Propuesta: ${c.accion_sugerida.toLowerCase()}.`,
        `5. Cierre: confirmar fecha de compromiso, agradecer y dejar el canal de contacto de la agencia.`,
      ].join("\n");
    }

    if (canal === "Visita") {
      return [
        `Puntos para la visita a ${c.cliente} (${c.distrito}):`,
        `• Presentarse e identificarse como ${firma}.`,
        `• Situación: ${c.dias_atraso} días de atraso, ${c.cuotas_vencidas} cuota(s) vencida(s), saldo ${soles(c.saldo_capital, 2)}.`,
        `• Escuchar la causa del atraso sin presionar.`,
        `• Proponer: ${c.accion_sugerida.toLowerCase()}.`,
        `• Dejar por escrito el acuerdo y la próxima fecha de contacto.`,
      ].join("\n");
    }

    const texto = {
      preventiva: `Hola ${nombre}, te saluda el ${firma}. Te recordamos que tu cuota de ${cuota} vence pronto. Si tienes alguna duda, respóndenos por aquí. ¡Gracias por tu puntualidad!`,
      temprana: `Hola ${nombre}, te saluda el ${firma}. Vemos que tu cuota de ${cuota} está pendiente. ¿Nos indicas una fecha en la que puedas pagarla? Si necesitas ayuda, estamos para apoyarte.`,
      intermedia: `Hola ${nombre}, te saluda el ${firma}. Queremos ayudarte a ponerte al día: podemos reprogramar tus cuotas. Respóndenos y coordinamos la mejor opción para ti.`,
      "tardía": `Hola ${nombre}, te saluda el ${firma}. Tenemos alternativas de refinanciamiento para tu crédito. Respóndenos o acércate a tu agencia y buscamos juntos una solución.`,
      prejudicial: `Hola ${nombre}, te saluda el ${firma}. Queremos ofrecerte una alternativa de acuerdo de pago para tu crédito. Comunícate con nosotros o acércate a tu agencia esta semana.`,
    }[c.tramo];
    return texto;
  }

  // ---------- Render ----------
  function renderKpis() {
    const r = datos.resumen;
    const urgentes = datos.creditos.filter((c) => c.urgencia >= 100).length;
    const enMora = datos.creditos.filter((c) => c.dias_atraso > 0).length;
    $("#kpis").innerHTML = [
      { etiqueta: "Créditos en la cartera", valor: r.creditos.toLocaleString("es-PE"), extra: `${enMora} con atraso` },
      { etiqueta: "Saldo total", valor: compacto(r.saldo_total), extra: "Saldo de capital" },
      { etiqueta: "Saldo en mora", valor: compacto(r.saldo_en_mora), extra: `${r.ratio_mora_pct}% de la cartera asignada` },
      { etiqueta: "Por cambiar de tramo", valor: urgentes, extra: "En 5 días o menos", destacado: true },
    ].map((k) => `
      <div class="kpi${k.destacado ? " kpi--destacado" : ""}">
        <div class="kpi__etiqueta">${k.etiqueta}</div>
        <div class="kpi__valor">${k.valor}</div>
        <div class="kpi__extra">${k.extra}</div>
      </div>`).join("");
  }

  function renderTramos() {
    const porTramo = datos.resumen.por_tramo;
    const max = Math.max(...Object.values(porTramo).map((t) => t.saldo));
    $("#tramos").innerHTML = datos.tramos.map((t) => {
      const d = porTramo[t.nombre];
      const rango = t.hasta === null ? `Más de ${t.desde - 1} días` : t.desde === t.hasta ? "Al día" : `${t.desde}–${t.hasta} días`;
      return `
        <button class="tramo" type="button" data-tramo="${t.nombre}" aria-pressed="${filtro.tramo === t.nombre}" style="--c:${COLOR_TRAMO[t.nombre]}">
          <div class="tramo__nombre">${t.nombre}</div>
          <div class="tramo__dias">${rango}</div>
          <div class="tramo__saldo">${compacto(d.saldo)}</div>
          <div class="tramo__barra"><span style="width:${(d.saldo / max) * 100}%"></span></div>
          <div class="tramo__creditos">${d.creditos} créditos</div>
        </button>`;
    }).join("");
  }

  function filtrados() {
    const q = filtro.texto.trim().toLowerCase();
    return datos.creditos.filter((c) =>
      (!filtro.tramo || c.tramo === filtro.tramo) &&
      (!filtro.distrito || c.distrito === filtro.distrito) &&
      (!filtro.producto || c.producto === filtro.producto) &&
      (!q || c.cliente.toLowerCase().includes(q) || c.id_credito.toLowerCase().includes(q))
    );
  }

  function renderRanking() {
    const lista = filtrados();
    const pagina = lista.slice(0, visibles);
    $("#conteo").textContent = `${lista.length} créditos · ordenados por prioridad`;
    $("#ver-mas").hidden = visibles >= lista.length;
    if (!lista.length) {
      $("#ranking").innerHTML = `<tr><td colspan="7" class="vacio">Ningún crédito cumple estos filtros.</td></tr>`;
      return;
    }
    $("#ranking").innerHTML = pagina.map((c, i) => `
      <tr class="fila" tabindex="0" data-id="${c.id_credito}" aria-label="Ver detalle de ${esc(c.cliente)}">
        <td class="num c-pos">${i + 1}</td>
        <td class="c-cliente">
          <div class="cliente__nombre">${esc(c.cliente)}</div>
          <div class="cliente__meta">${c.id_credito} · ${esc(c.producto)} · ${esc(c.distrito)}</div>
        </td>
        <td class="c-tramo"><span class="chip" style="--c:${COLOR_TRAMO[c.tramo]}">${c.tramo}</span><span class="solo-movil">${c.dias_atraso} días · ${soles(c.saldo_capital)}</span></td>
        <td class="num c-dias">${c.dias_atraso}</td>
        <td class="num c-saldo">${soles(c.saldo_capital)}</td>
        <td class="c-prioridad">
          <div class="prioridad">
            <span class="prioridad__valor">${c.prioridad.toFixed(1)}</span>
            <span class="prioridad__barra"><span style="width:${c.prioridad}%"></span></span>
          </div>
        </td>
        <td class="c-accion"><span class="accion">${esc(c.accion_sugerida)}<small>${esc(c.canal_sugerido)}</small></span></td>
      </tr>`).join("");
  }

  function abrirDetalle(id) {
    const c = datos.creditos.find((x) => x.id_credito === id);
    if (!c) return;
    const p = datos.pesos;
    const componentes = [
      ["Urgencia", c.urgencia, p.urgencia],
      ["Recuperabilidad", c.recuperabilidad, p.recuperabilidad],
      ["Exposición", c.exposicion, p.exposicion],
    ];
    const canalTitulo = c.canal_sugerido === "Llamada" ? "Guion de llamada" : c.canal_sugerido === "Visita" ? "Puntos para la visita" : `Mensaje por ${c.canal_sugerido}`;
    $("#detalle-contenido").innerHTML = `
      <div class="detalle__cabecera">
        <div>
          <h2 id="detalle-titulo">${esc(c.cliente)}</h2>
          <div class="detalle__sub">${c.id_credito} · ${esc(c.producto)} · ${esc(c.distrito)} · puesto ${c.posicion} de ${datos.creditos.length}</div>
        </div>
        <button class="cerrar" type="button" data-cerrar aria-label="Cerrar">✕</button>
      </div>

      <div class="puntaje">
        <div class="puntaje__valor">${c.prioridad.toFixed(1)}</div>
        <div class="puntaje__texto">puntaje de prioridad<br><span class="chip" style="--c:${COLOR_TRAMO[c.tramo]};text-transform:none">mora ${c.tramo} · ${c.dias_atraso} días</span></div>
      </div>

      <div class="componentes">
        ${componentes.map(([n, v, w]) => `
          <div>
            <div class="componente__fila"><span>${n} <small style="color:var(--texto-2)">(${Math.round(w * 100)}%)</small></span><span>${v.toFixed(1)}</span></div>
            <div class="componente__barra"><span style="width:${v}%"></span></div>
          </div>`).join("")}
      </div>

      <dl class="datos">
        <div><dt>Saldo de capital</dt><dd>${soles(c.saldo_capital, 2)}</dd></div>
        <div><dt>Cuota mensual</dt><dd>${soles(c.cuota_mensual, 2)}</dd></div>
        <div><dt>Cuotas vencidas</dt><dd>${c.cuotas_vencidas}</dd></div>
        <div><dt>Pagos puntuales (12 meses)</dt><dd>${c.pagos_puntuales_12m} de 12</dd></div>
        <div><dt>Promesas incumplidas</dt><dd>${c.promesas_incumplidas}</dd></div>
        <div><dt>Último contacto</dt><dd>hace ${c.dias_desde_ultimo_contacto} días</dd></div>
        <div><dt>Canal preferido</dt><dd>${esc(c.canal_preferido)}</dd></div>
        <div><dt>Garantía</dt><dd>${c.tiene_garantia ? "Sí" : "No"}</dd></div>
      </dl>

      ${c.motivos.length ? `<h3>Por qué está en este puesto</h3><ul class="motivos">${c.motivos.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>` : ""}

      <div class="caja-accion">
        <strong>${esc(c.accion_sugerida)}</strong>
        <span>Canal sugerido: ${esc(c.canal_sugerido)}</span>
      </div>

      <div class="mensaje__cabecera">
        <h3>${canalTitulo}</h3>
        <button class="boton boton--secundario" type="button" data-copiar>Copiar</button>
      </div>
      <pre class="mensaje" id="mensaje">${esc(mensajePara(c))}</pre>
      <p class="mensaje__nota">Plantilla base. El agente de IA (Gemini) la personaliza según la conversación con el gestor.</p>
    `;
    const dlg = $("#detalle");
    if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
  }

  // ---------- Eventos ----------
  function aplicar() {
    visibles = PASO;
    renderTramos();
    renderRanking();
  }

  function llenarSelect(sel, valores) {
    sel.insertAdjacentHTML("beforeend", valores.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join(""));
  }

  function enlazar() {
    $("#buscar").addEventListener("input", (e) => { filtro.texto = e.target.value; aplicar(); });
    $("#f-tramo").addEventListener("change", (e) => { filtro.tramo = e.target.value; aplicar(); });
    $("#f-distrito").addEventListener("change", (e) => { filtro.distrito = e.target.value; aplicar(); });
    $("#f-producto").addEventListener("change", (e) => { filtro.producto = e.target.value; aplicar(); });
    $("#limpiar").addEventListener("click", () => {
      Object.assign(filtro, { texto: "", tramo: "", distrito: "", producto: "" });
      ["#buscar", "#f-tramo", "#f-distrito", "#f-producto"].forEach((s) => ($(s).value = ""));
      aplicar();
    });
    $("#tramos").addEventListener("click", (e) => {
      const b = e.target.closest(".tramo");
      if (!b) return;
      filtro.tramo = filtro.tramo === b.dataset.tramo ? "" : b.dataset.tramo;
      $("#f-tramo").value = filtro.tramo;
      aplicar();
    });
    $("#ver-mas").addEventListener("click", () => { visibles += PASO; renderRanking(); });
    $("#ranking").addEventListener("click", (e) => {
      const fila = e.target.closest(".fila");
      if (fila) abrirDetalle(fila.dataset.id);
    });
    $("#ranking").addEventListener("keydown", (e) => {
      const fila = e.target.closest(".fila");
      if (fila && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); abrirDetalle(fila.dataset.id); }
    });
    const dlg = $("#detalle");
    dlg.addEventListener("click", (e) => {
      if (e.target === dlg || e.target.closest("[data-cerrar]")) dlg.close();
      const copiar = e.target.closest("[data-copiar]");
      if (copiar) {
        navigator.clipboard?.writeText($("#mensaje").textContent).then(() => {
          copiar.textContent = "Copiado";
          setTimeout(() => (copiar.textContent = "Copiar"), 1500);
        }).catch(() => {});
      }
    });
  }

  async function iniciar() {
    try {
      const resp = await fetch("datos.json", { cache: "no-cache" });
      datos = await resp.json();
    } catch (err) {
      $("#ranking").innerHTML = `<tr><td colspan="7" class="vacio">No se pudieron cargar los datos. Genera web/datos.json con: python scripts/exportar_panel.py</td></tr>`;
      return;
    }
    llenarSelect($("#f-tramo"), datos.tramos.map((t) => t.nombre));
    llenarSelect($("#f-distrito"), [...new Set(datos.creditos.map((c) => c.distrito))].sort());
    llenarSelect($("#f-producto"), [...new Set(datos.creditos.map((c) => c.producto))].sort());
    $("#generado").textContent = `Datos ficticios generados el ${datos.generado}`;
    renderKpis();
    enlazar();
    aplicar();
  }

  iniciar();
})();
