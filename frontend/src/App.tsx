import { useState, useEffect } from 'react';

function App() {
  const [globalConfig, setGlobalConfig] = useState({ target_url: '', global_proxy: '' });
  const [emails, setEmails] = useState<any[]>([]);
  const [newEmail, setNewEmail] = useState({ email: '', password: '', imap_server: '', imap_port: 993, proxy_url: '' });

  useEffect(() => {
    fetchGlobal();
    fetchEmails();
  }, []);

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

  const addEmail = async () => {
    if(!newEmail.email || !newEmail.password || !newEmail.imap_server) {
      alert('请将必填项（邮箱、密码、服务器地址）填写完整'); return;
    }
    await fetch('/api/v1/config/emails', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newEmail)
    });
    setNewEmail({ email: '', password: '', imap_server: '', imap_port: 993, proxy_url: '' });
    fetchEmails();
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
          <input value={globalConfig.global_proxy || ''} onChange={e => setGlobalConfig({...globalConfig, global_proxy: e.target.value})} placeholder="例如: socks5://192.168.1.100:10808" />
        </div>
        <button onClick={saveGlobal}>💾 立即应用全局配置</button>
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
              <button style={{backgroundColor: '#10b981', padding: '0.5rem 1rem'}} onClick={() => testEmail(acc.id)}>📶 连通测试</button>
              <button className="danger" onClick={() => delEmail(acc.id)}>删除</button>
            </div>
          </div>
        ))}
        {emails.length === 0 && <div style={{ color: 'var(--text-dim)', marginBottom: '1rem', padding: '1rem', background: 'var(--bg)', borderRadius: '8px' }}>🚀您目前没有关联任何邮箱。填在下方的即刻便能收信！</div>}

        <div style={{ marginTop: '2rem', padding: '1.5rem', background: 'var(--bg)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
          <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>增加需要监控提取的新邮箱</h3>
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
          <button onClick={addEmail}>➕ 放进后台实时运转序列</button>
        </div>
      </section>
    </div>
  );
}

export default App;
