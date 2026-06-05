export default function ConsultAnswer({ data }) {
  if (data.error) return <div className="ans-error">⚠ 出错了：{data.error}</div>

  if (data.refused) {
    return (
      <div className="ans-refused">
        <div className="refused-head">⛔ 该问题已拒答并转介</div>
        <p>{data.answer}</p>
        <p className="ans-disclaimer">{data.disclaimer}</p>
      </div>
    )
  }

  if (data.insufficientLiterature) {
    return (
      <div className="ans-insufficient">
        <div className="insuf-head">📚 文献不足，暂无法给出循证建议</div>
        <p>{data.suggestions?.[0]?.text}</p>
        {data.cautions?.length > 0 && (
          <ul>{data.cautions.map((c, i) => <li key={i}>{c}</li>)}</ul>
        )}
        <p className="ans-disclaimer">{data.disclaimer}</p>
      </div>
    )
  }

  const Refs = ({ refs }) => (
    <>{(refs || []).map((r) => <sup className="ref-badge" key={r}>[{r}]</sup>)}</>
  )
  const WebRefs = ({ refs }) => (
    <>{(refs || []).map((r) => <sup className="ref-badge-web" key={r}>[{r}]</sup>)}</>
  )

  return (
    <div className="ans">
      {data.literatureMissing && (
        <div className="web-missing-banner">
          未命中本地权威文献，以下为网络补充信息，请结合专业评估使用。
        </div>
      )}
      <section className="ans-sec">
        <h4>💡 建议方向</h4>
        <ol>
          {(data.suggestions || []).map((s, i) => (
            <li key={i}>
              {s.text}
              <Refs refs={s.refs} />
              <WebRefs refs={s.webRefs} />
            </li>
          ))}
        </ol>
      </section>

      {(data.cautions?.length > 0) && (
        <section className="ans-sec">
          <h4>⚠ 注意事项</h4>
          <ul>{data.cautions.map((c, i) => <li key={i}>{c}</li>)}</ul>
        </section>
      )}

      {(data.whenToSeeDoctor?.length > 0) && (
        <section className="ans-sec">
          <h4>🏥 何时需就医</h4>
          <ul>{data.whenToSeeDoctor.map((c, i) => <li key={i}>{c}</li>)}</ul>
        </section>
      )}

      {data.citations?.length > 0 && (
        <details className="ans-cite">
          <summary>📚 文献依据（{data.citations.length}）</summary>
          {data.citations.map((c) => (
            <div className="cite-item" key={c.id}>
              <div className="cite-head"><span className="cite-no">[{c.id}]</span> {c.source} <em>· {c.loc}</em></div>
              <div className="cite-snippet">{c.snippet}</div>
            </div>
          ))}
        </details>
      )}

      {data.webCitations?.length > 0 && (
        <details className="ans-cite ans-web-cite">
          <summary>🌐 网络参考（补充，{data.webCitations.length}）</summary>
          {data.webCitations.map((c) => (
            <div className="cite-item" key={c.id}>
              <div className="cite-head">
                <span className="cite-no cite-no-web">[{c.id}]</span> {c.title}
                {c.url && (
                  <> · <a href={c.url} target="_blank" rel="noopener noreferrer">{c.url}</a></>
                )}
              </div>
              <div className="cite-snippet">{c.snippet}</div>
            </div>
          ))}
        </details>
      )}

      {data.disclaimer && <p className="ans-disclaimer">{data.disclaimer}</p>}
    </div>
  )
}
