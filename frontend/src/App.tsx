import { useState, useEffect } from 'react';

function App() {
  const [globalConfig, setGlobalConfig] = useState({ target_url: '', global_proxy: '' });
  const [emails, setEmails] = useState<any[]>([]);
  const [newEmail, setNewEmail] = useState({ email: '', password: '', imap_server: '', imap_port: 993, proxy_url: '' });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    fetchGlobal();
    fetchEmails();
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    const res = await fetch('/api/v1/config/logs');
    if(res.ok) setLogs(await res.json());
  };

  const fetchGlobal = async () => {
    const res = await fetch('/api/v1/config/global');
    if(res.ok) setGlobalConfig(await res.json());
  };

  const fetchEmails = async () => {
    const res = await fetch('/api/v1/config/emails');
    if(res.ok) setEmails(await res.json());
  };

  const saveGlobal = async () => {
    await fetch('/api/v1/config/global', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(globalConfig)
    });
    alert('✅ 全局配置已成功保存并在后台实时生效！');
  };

  const testGlobalWebhook = async () => {
    const res = await fetch('/api/v1/config/global/test', { method: 'POST' });
    const result = await res.json();
    alert(result.status === 'success' ? `🟢 ${result.msg}` : `🔴 ${result.msg}`);
    setTimeout(fetchLogs, 1500); // 过两秒捞取最新的推流报错明细
  };

  const addOrUpdateEmail = async () => {
    if(!newEmail.email || !newEmail.password || !newEmail.imap_server) {
      alert('请将必填项（邮箱、密码、服务器地址）填写完整'); return;
    }
    
    if (editingId !== null) {
      await fetch(`/api/v1/config/emails/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEmail)
      });
      alert('✅ 对应的邮箱监控规则已成功更新');
    } else {
      await fetch('/api/v1/config/emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEmail)
      });
    }
    
    setNewEmail({ email: '', password: '', imap_server: '', imap_port: 993, proxy_url: '' });
    setEditingId(null);
    fetchEmails();
  };

  const editEmail = (acc: any) => {
    setNewEmail({ email: acc.email, password: acc.password, imap_server: acc.imap_server, imap_port: acc.imap_port, proxy_url: acc.proxy_url || '' });
    setEditingId(acc.id);
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  };

  const cancelEdit = () => {
    setNewEmail({ email: '', password: '', imap_server: '', imap_port: 993, proxy_url: '' });
    setEditingId(null);
  };

  const delEmail = async (id: number) => {
    if(window.confirm('您确定要删掉这个邮箱的监控任务吗？')) {
      await fetch(`/api/v1/config/emails/${id}`, { method: 'DELETE' });
      fetchEmails();
    }
  };

  const testEmail = async (id: number) => {
    // 简易的弹窗让用户感知加载
    window.alert('⏳ 正在跨接网络请求并尝试搜索最近收件箱中的验证码，这可能需要十秒钟左右，点击确定后请稍等不要刷新...');
    try {
      const res = await fetch(`/api/v1/config/emails/${id}/test`);
      const result = await res.json();
      if(result.status === 'success') {
          if(result.data) {
              window.alert(`✅ ${result.msg}\n\n🕵️ 侦测到历史验证码:\n【时间】: ${result.data.date}\n【验证码】: ${result.data.code}\n【邮件标题】: ${result.data.subject}`);
          } else {
              window.alert(`✅ ${result.msg}`);
          }
      } else {
          window.alert(`❌ 测试失败: ${result.msg}`);
      }
    } catch(e) {
      window.alert(`💔 测试请求发生网络异常或后端无响应!`);
    }
  };

  return (
    <div className="container">
      <header style={{ marginBottom: '3rem', textAlign: 'center', marginTop: '2rem' }}>
        <h1>宅家验证码 服务中枢</h1>
        <p style={{ color: 'var(--text-dim)' }}>在这里统一添加手机分发信息与邮箱监控规则</p>
      </header>

      <section className="card">
        <h2>全局配置</h2>
        <div className="form-group">
          <label>目标 Webhook URL (成功截获的验证码短信息将全发往这里)</label>
          <input value={globalConfig.target_url || ''} onChange={e => setGlobalConfig({...globalConfig, target_url: e.target.value})} placeholder="例如: https://qyapi.weixin.qq... (钉钉/企业微信群机器人地址)" />
        </div>
        <div className="form-group">
          <label>NAS 全局代理 (给全系统兜底使用，如果不填则直连中国大陆网络)</label>
          <input value={globalConfig.global_proxy || ''} onChange={e => setGlobalConfig({...globalConfig, global_proxy: e.target.value})} placeholder="例如: socks5://10.0.0.210:7891" />
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button onClick={saveGlobal}>💾 立即应用全局配置</button>
          <button style={{ backgroundColor: '#10b981' }} onClick={testGlobalWebhook}>🔗 测试 Webhook</button>
        </div>
      </section>

      <section className="card">
        <h2>监听邮箱与代理隔离管理</h2>
        {emails.map((acc: any) => (
          <div key={acc.id} className="table-row">
            <div>
              <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{acc.email}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                IMAP 服务器: {acc.imap_server}:{acc.imap_port}
                {acc.proxy_url ? <span style={{color: 'var(--primary)', marginLeft: 8}}>🚀专属代理生效中: {acc.proxy_url}</span> : <span style={{marginLeft: 8}}>🟢未挂专属直连中</span>}
              </div>
            </div>
            <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
              <button style={{backgroundColor: '#10b981', padding: '0.4rem 0.8rem'}} onClick={() => testEmail(acc.id)}>📶 测试</button>
              <button style={{backgroundColor: '#6366f1', padding: '0.4rem 0.8rem'}} onClick={() => editEmail(acc)}>编辑</button>
              <button className="danger" onClick={() => delEmail(acc.id)}>删除</button>
            </div>
          </div>
        ))}
        {emails.length === 0 && <div style={{ color: 'var(--text-dim)', marginBottom: '1rem', padding: '1rem', background: 'var(--bg)', borderRadius: '8px' }}>🚀您目前没有关联任何邮箱。填在下方的即刻便能收信！</div>}

        <div style={{ marginTop: '2rem', padding: '1.5rem', background: 'var(--bg)', borderRadius: '8px', border: editingId ? '1px solid var(--primary)' : '1px dashed var(--border)' }}>
          <h3 style={{ marginTop: 0, color: editingId ? 'var(--primary)' : 'var(--text)' }}>
            {editingId ? '🛠️ 正在修改邮箱配置' : '加需要监控提取的新邮箱'}
          </h3>
          <div className="row">
            <div className="form-group">
              <label>目标邮箱地址</label>
              <input value={newEmail.email} onChange={e => setNewEmail({...newEmail, email: e.target.value})} placeholder="yourname@gmail.com" />
            </div>
            <div className="form-group">
              <label>邮箱应用专属密码 (切勿使用登入原密码)</label>
              <input type="password" value={newEmail.password} onChange={e => setNewEmail({...newEmail, password: e.target.value})} />
            </div>
          </div>
          <div className="row">
            <div className="form-group">
              <label>IMAP 地址提供商</label>
              <input value={newEmail.imap_server} onChange={e => setNewEmail({...newEmail, imap_server: e.target.value})} placeholder="imap.gmail.com" />
            </div>
            <div className="form-group">
              <label>特定专属代理 (这允许你单独让谷歌邮箱翻墙而不卡顿国内邮箱)</label>
              <input value={newEmail.proxy_url} onChange={e => setNewEmail({...newEmail, proxy_url: e.target.value})} placeholder="选填, 不填跟随全局" />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button onClick={addOrUpdateEmail}>{editingId ? '💾 保存当前修改' : '➕ 放进后台实时运转序列'}</button>
            {editingId && <button style={{ backgroundColor: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)' }} onClick={cancelEdit}>取消修改</button>}
          </div>
        </div>
      </section>

      {/* 高大上的仿纯黑极客终端日志面板区 */}
      <section className="card" style={{ backgroundColor: '#000', borderColor: '#333' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ color: '#0f0', margin: 0, fontFamily: 'monospace', fontSize: '1.1rem' }}>&gt;_ 全局运行日志 (System Terminal)</h2>
          <button style={{ backgroundColor: 'transparent', border: '1px solid #334155', padding: '0.4rem 0.8rem', fontSize: '0.8rem' }} onClick={fetchLogs}>🔄 刷新缓存</button>
        </div>
        <div style={{ maxHeight: '400px', overflowY: 'auto', padding: '1rem', background: '#111', borderRadius: '8px', border: '1px solid #222', fontFamily: '"Courier New", Courier, monospace', fontSize: '0.85rem', lineHeight: 1.6 }}>
          {logs.length === 0 && <div style={{ color: '#555' }}>[No Logs Found] 系统一切正常犹如处女地...</div>}
          {logs.map((log) => {
             const color = log.level === 'ERROR' ? '#ff4081' : (log.level === 'WARNING' ? '#ffc107' : '#2196f3');
             return (
               <div key={log.id} style={{ display: 'flex', gap: '12px', borderBottom: '1px solid #1a1a1a', padding: '4px 0' }}>
                 <span style={{ color: '#6b7280', whiteSpace: 'nowrap' }}>[{log.created_at || '刚才'}]</span>
                 <span style={{ color, whiteSpace: 'nowrap', fontWeight: 600, width: '60px' }}>{log.level}</span>
                 <span style={{ color: '#fff' }}><span style={{ color: '#9ca3af', marginRight: '6px' }}>&lt;{log.source}&gt;</span>{log.message}</span>
               </div>
             );
          })}
        </div>
      </section>
    </div>
  );
}

export default App;
