import { useEffect } from 'react'

/** Sets `document.title` for as long as the calling screen is mounted, so a
 * nurse with several tabs open (or a screen reader) can tell them apart.
 * Restores whatever title was there before on unmount. */
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    const previous = document.title
    document.title = title
    return () => {
      document.title = previous
    }
  }, [title])
}

export default useDocumentTitle
