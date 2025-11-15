import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Package, BarChart3, Settings, Menu, X, LogOut, User, Home } from 'lucide-react';
import { useRouter } from 'next/router';
import styled from 'styled-components';
import { colors, radius, shadows, typography } from '@/styles/tokens';

interface PainelLayoutProps {
  children: React.ReactNode;
  titulo: string;
  tipoUsuario: 'vendedor' | 'anunciador' | 'gestor';
}

interface MenuItem {
  nome: string;
  icone: React.ReactNode;
  href: string;
  ativo?: boolean;
}

const Container = styled.div`
  min-height: 100vh;
  background: ${colors.background};
`;

const SidebarDesktop = styled(motion.div)`
  position: fixed;
  left: 0;
  top: 0;
  height: 100%;
  width: 256px;
  z-index: 40;
  display: none;
  @media (min-width: 1024px) { display: block; }
`;

const GlassPanel = styled.div`
  height: 100%;
  margin: 16px;
  margin-right: 0;
  background: ${colors.card};
  backdrop-filter: blur(14px);
  border-radius: ${radius.lg};
  box-shadow: ${shadows.base};
  border: 1px solid ${colors.border};
`;

const PanelContent = styled.div`
  padding: 24px;
`;

const Brand = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
`;

const BrandLogo = styled.div`
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, ${colors.primary}, ${colors.secondary});
  display: flex;
  align-items: center;
  justify-content: center;
`;

const Nav = styled.nav`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const NavLink = styled(motion.a)<{ $active?: boolean }>`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  color: ${({ $active }) => ($active ? colors.primary : colors.textLight)};
  background: ${({ $active }) => ($active ? 'rgba(99,102,241,0.08)' : 'transparent')};
  border-left: ${({ $active }) => ($active ? `4px solid ${colors.primary}` : '4px solid transparent')};
`;

const LogoutWrap = styled.div`
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 24px;
`;

const LogoutBtn = styled.button`
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  background: ${colors.card};
  border: 1px solid ${colors.border};
  color: ${colors.textLight};
`;

const MobileHeader = styled.div`
  display: block;
  @media (min-width: 1024px) { display: none; }
  margin: 16px;
  background: ${colors.card};
  backdrop-filter: blur(14px);
  border-radius: ${radius.lg};
  box-shadow: ${shadows.base};
  border: 1px solid ${colors.border};
`;

const HeaderRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
`;

const Overlay = styled(motion.div)`
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 50;
  @media (min-width: 1024px) { display: none; }
`;

const Drawer = styled(motion.div)`
  position: fixed;
  left: 0;
  top: 0;
  height: 100%;
  width: 256px;
  z-index: 50;
  @media (min-width: 1024px) { display: none; }
`;

const Main = styled.div`
  min-height: 100vh;
  @media (min-width: 1024px) { margin-left: 288px; }
`;

const HeaderGlass = styled(motion.div)`
  margin: 16px;
  background: ${colors.card};
  backdrop-filter: blur(14px);
  border-radius: ${radius.lg};
  box-shadow: ${shadows.base};
  border: 1px solid ${colors.border};
`;

const HeaderInner = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
`;

const PageTitle = styled.h1`
  font-size: 20px;
  font-weight: ${typography.weightSemibold};
  color: ${colors.textDark};
`;

const PageSub = styled.p`
  font-size: 13px;
  color: ${colors.textLight};
  text-transform: capitalize;
  margin-top: 4px;
`;

const ContentPad = styled.div`
  padding: 16px;
  @media (min-width: 1024px) { padding: 24px; }
`;

export default function PainelLayout({ children, titulo, tipoUsuario }: PainelLayoutProps) {
  const [sidebarAberto, setSidebarAberto] = useState(false);
  const router = useRouter();

  const menuVendedor: MenuItem[] = [
    { nome: 'Dashboard', icone: <Home size={20} />, href: '/vendedores' },
    { nome: 'Estoque', icone: <Package size={20} />, href: '/vendedores/estoque', ativo: router.pathname === '/vendedores/estoque' },
    { nome: 'Configurações', icone: <Settings size={20} />, href: '/vendedores/configuracoes' },
  ];

  const menuAnunciador: MenuItem[] = [
    { nome: 'Dashboard', icone: <Home size={20} />, href: '/anunciador' },
    { nome: 'Estoque', icone: <Package size={20} />, href: '/anunciador/estoque', ativo: router.pathname === '/anunciador/estoque' },
    { nome: 'Sincronização', icone: <BarChart3 size={20} />, href: '/anunciador/sincronizacao' },
    { nome: 'Configurações', icone: <Settings size={20} />, href: '/anunciador/configuracoes' },
  ];

  const menuGestor: MenuItem[] = [
    { nome: 'Dashboard', icone: <Home size={20} />, href: '/gestor' },
    { nome: 'Estoque', icone: <Package size={20} />, href: '/gestor/estoque' },
    { nome: 'Configurações', icone: <Settings size={20} />, href: '/gestor/configuracoes' },
  ];

  const menuItems = tipoUsuario === 'vendedor' ? menuVendedor : tipoUsuario === 'anunciador' ? menuAnunciador : menuGestor;

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  return (
    <Container>
      <SidebarDesktop initial={{ x: -280 }} animate={{ x: 0 }}>
        <GlassPanel>
          <PanelContent>
            <Brand>
              <BrandLogo>
                <Package size={24} color={colors.white} />
              </BrandLogo>
              <div>
                <div style={{ fontWeight: 700, color: colors.textDark }}>DL Auto Peças</div>
                <div style={{ fontSize: 12, color: colors.textLight, textTransform: 'capitalize' }}>{tipoUsuario}</div>
              </div>
            </Brand>

            <Nav>
              {menuItems.map((item, index) => (
                <NavLink key={item.nome} href={item.href} $active={item.ativo} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.1 }}>
                  {item.icone}
                  <span style={{ fontWeight: typography.weightMedium }}>{item.nome}</span>
                </NavLink>
              ))}
            </Nav>
          </PanelContent>
          <LogoutWrap>
            <LogoutBtn onClick={handleLogout}>
              <LogOut size={18} />
              <span style={{ fontWeight: typography.weightMedium }}>Sair</span>
            </LogoutBtn>
          </LogoutWrap>
        </GlassPanel>
      </SidebarDesktop>

      <MobileHeader>
        <HeaderRow>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <BrandLogo style={{ width: 32, height: 32 }}>
              <Package size={18} color={colors.white} />
            </BrandLogo>
            <div>
              <div style={{ fontWeight: 700, color: colors.textDark, fontSize: 14 }}>DL Auto Peças</div>
              <div style={{ fontSize: 12, color: colors.textLight, textTransform: 'capitalize' }}>{tipoUsuario}</div>
            </div>
          </div>
          <button onClick={() => setSidebarAberto(true)} style={{ padding: 8, borderRadius: 8, border: 'none', background: 'transparent', color: colors.textLight }}>
            <Menu size={20} />
          </button>
        </HeaderRow>
      </MobileHeader>

      <AnimatePresence>
        {sidebarAberto && (
          <>
            <Overlay initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSidebarAberto(false)} />
            <Drawer initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }}>
              <GlassPanel>
                <PanelContent>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <BrandLogo style={{ width: 32, height: 32 }}>
                        <Package size={18} color={colors.white} />
                      </BrandLogo>
                      <div>
                        <div style={{ fontWeight: 700, color: colors.textDark, fontSize: 14 }}>DL Auto Peças</div>
                        <div style={{ fontSize: 12, color: colors.textLight, textTransform: 'capitalize' }}>{tipoUsuario}</div>
                      </div>
                    </div>
                    <button onClick={() => setSidebarAberto(false)} style={{ padding: 8, borderRadius: 8, border: 'none', background: 'transparent', color: colors.textLight }}>
                      <X size={20} />
                    </button>
                  </div>

                  <Nav>
                    {menuItems.map((item) => (
                      <NavLink key={item.nome} href={item.href} $active={item.ativo}>
                        {item.icone}
                        <span style={{ fontWeight: typography.weightMedium, fontSize: 14 }}>{item.nome}</span>
                      </NavLink>
                    ))}
                  </Nav>
                </PanelContent>
                <LogoutWrap>
                  <LogoutBtn onClick={handleLogout}>
                    <LogOut size={18} />
                    <span style={{ fontWeight: typography.weightMedium, fontSize: 14 }}>Sair</span>
                  </LogoutBtn>
                </LogoutWrap>
              </GlassPanel>
            </Drawer>
          </>
        )}
      </AnimatePresence>

      <Main>
        <HeaderGlass initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
          <HeaderInner>
            <div>
              <PageTitle>{titulo}</PageTitle>
              <PageSub>Painel do {tipoUsuario === 'vendedor' ? 'Vendedor' : tipoUsuario === 'anunciador' ? 'Anunciador' : 'Gestor'}</PageSub>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: 999, background: 'rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <User size={16} color={colors.secondary} />
              </div>
              <span style={{ fontSize: 14, fontWeight: typography.weightMedium, color: colors.textDark, display: 'none' }}>Usuário</span>
            </div>
          </HeaderInner>
        </HeaderGlass>
        <ContentPad>{children}</ContentPad>
      </Main>
    </Container>
  );
}