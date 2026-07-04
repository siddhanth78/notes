class Tree:
    def __init__(self):
        self.root = TreeNode()

    def insert(self, word):
        curr_node = self.root
        for w in word:
            if w not in curr_node.children:
                new_node = TreeNode()
                curr_node.children[w] = new_node
            curr_node = curr_node.children[w]
        curr_node.isEOW = True

    def is_exists(self, prefix, prefix_check=False):
        curr_node = self.root
        for p in prefix:
            if p not in curr_node.children:
                return False
            curr_node = curr_node.children[p]
        if prefix_check == False:
            return (curr_node.isEOW, None)
        else:
            return (True, curr_node)

    def suggest(self, prefix):
        all_suggestions = [prefix]
        flag, curr_node = self.is_exists(prefix, True)
        if flag == True:
            def traverseTree(node, curr_word):
                if node.isEOW:
                    all_suggestions.append(curr_word)
                for char_, child in node.children.items():
                    traverseTree(child, curr_word + char_)

            traverseTree(curr_node, prefix)
        return all_suggestions

    def remove(self, word):
        def should_delete(node, word, depth):
            if not node:
                return False

            if depth == len(word):
                if node.isEOW == False:
                    return False

                node.isEOW = False
                return len(node.children) == 0

            char_ = word[depth]
            if char_ not in node.children:
                return False

            del_flag = should_delete(node.children[char_], word, depth+1)

            if del_flag == True:
                del node.children[char_]
                return not node.isEOW and len(node.children) == 0

            return False

        should_delete(self.root, word, 0)

class TreeNode:
    def __init__(self):
        self.children = {}
        self.isEOW = False

def main():
    tree = Tree()
    tree.insert("apple")
    tree.insert("apricot")
    tree.insert("banana")
    print(tree.suggest("ap"))
    tree.remove("apricot")
    print(tree.suggest("ap"))
        
if __name__ == "__main__":
    main()
