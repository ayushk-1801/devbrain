import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { DocsBody, DocsPage as FumadocsPage } from 'fumadocs-ui/layouts/docs/page';
import { RootProvider } from 'fumadocs-ui/provider/react-router';
import defaultMdxComponents from 'fumadocs-ui/mdx';
import { Accordion, Accordions } from 'fumadocs-ui/components/accordion';
import { Callout } from 'fumadocs-ui/components/callout';
import { Step, Steps } from 'fumadocs-ui/components/steps';
import { Card, Cards } from 'fumadocs-ui/components/card';
import { TypeTable } from 'fumadocs-ui/components/type-table';
import { Logo } from './ui/Logo';

const Provider = RootProvider as any;
const PageLayout = FumadocsPage as any;

export default function DocsPage() {
  useEffect(() => {
    document.title = "DevBrain - Docs";
    return () => {
      document.title = "DevBrain";
    };
  }, []);

  const params = useParams();
  const slugParam = params['*'] || '';
  const slugs = slugParam.split('/').filter(Boolean);

  const page = source.getPage(slugs);

  // Fallback to first page if slug is empty
  const activePage = page || (slugs.length === 0 ? source.getPages()[0] : null);

  if (!activePage) {
    return (
      <Provider search={{ enabled: false }}>
        <DocsLayout
          tree={source.getPageTree()}
          githubUrl="https://github.com/ayushk-1801/devbrain"
          nav={{
            title: (
              <span className="flex items-center gap-2 pl-1.5">
                <Logo className="h-4 w-auto text-text-primary" />
                <span className="text-[12px] font-mono font-medium text-text-muted tracking-wider mt-0.5">DOCS</span>
              </span>
            ),
          }}
        >
          <div className="flex flex-col items-center justify-center min-h-[50vh] text-center p-8">
            <h1 className="text-4xl font-bold mb-4">404 - Docs Page Not Found</h1>
            <p className="text-muted-foreground mb-6">
              The documentation page you are looking for does not exist.
            </p>
            <Link
              to="/docs"
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:opacity-90 font-medium"
            >
              Back to Docs Home
            </Link>
          </div>
        </DocsLayout>
      </Provider>
    );
  }

  const data = activePage.data as any;
  const MDX = data.body;

  // Let's customize components so links use React Router's Link instead of native anchor tags
  const mdxComponents = {
    ...defaultMdxComponents,
    Accordion,
    Accordions,
    Callout,
    Step,
    Steps,
    Card,
    Cards,
    TypeTable,
    a: ({ href, children, ...props }: any) => {
      const isInternal = href && (href.startsWith('/') || href.startsWith('.'));
      if (isInternal) {
        return (
          <Link to={href} {...props}>
            {children}
          </Link>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
          {children}
        </a>
      );
    },
  };

  return (
    <Provider search={{ enabled: false }}>
      <DocsLayout
        tree={source.getPageTree()}
        githubUrl="https://github.com/ayushk-1801/devbrain"
        nav={{
          title: (
            <span className="flex items-center gap-2 pl-1.5">
              <Logo className="h-4 w-auto text-text-primary" />
              <span className="text-[12px] font-mono font-medium text-text-muted tracking-wider mt-0.5">DOCS</span>
            </span>
          ),
        }}
      >
        <PageLayout
          toc={data.exports?.toc || data._exports?.toc || data.toc}
          tableOfContent={{ enabled: true }}
        >
          <DocsBody>
            <h1 className="text-3xl font-extrabold tracking-tight mb-6">
              {data.title}
            </h1>
            <MDX components={mdxComponents} />
          </DocsBody>
        </PageLayout>
      </DocsLayout>
    </Provider>
  );
}
