import logging
import time
import collections
from common.yavide_utils import YavideUtils
from services.parser.ast_node_identifier import ASTNodeId
from services.parser.clang_parser import ChildVisitResult
from services.parser.ctags_parser import CtagsTokenizer

class VimSyntaxGenerator:
    def __init__(self, yavide_instance, output_syntax_file):
        self.yavide_instance = yavide_instance
        self.output_syntax_file = output_syntax_file

    def __call__(self, tunit, clang_parser, args):
        def visitor(ast_node, ast_parent_node, client_data):
            if ast_node.location.file and ast_node.location.file.name == tunit.spelling:  # we're only interested in symbols from associated translation unit
                ast_node_id = client_data.clang_parser.get_ast_node_id(ast_node)
                if ast_node_id != ASTNodeId.getUnsupportedId():
                    highlight_rule = VimSyntaxGenerator.__tag_id_to_vim_syntax_group(ast_node_id) + " " + client_data.clang_parser.get_ast_node_name(ast_node)
                    client_data.vim_syntax_element.append(
                        "call matchaddpos('" +
                        str(VimSyntaxGenerator.__tag_id_to_vim_syntax_group(ast_node_id)) +
                        "', [[" +
                        str(client_data.clang_parser.get_ast_node_line(ast_node)) +
                        ", " +
                        str(client_data.clang_parser.get_ast_node_column(ast_node)) +
                        ", " +
                        str(len(client_data.clang_parser.get_ast_node_name(ast_node))) +
                        "]], -1)" +
                        "\n"
                    )
                else:
                    logging.debug("Unsupported token id: [{0}, {1}]: {2} '{3}'".format(
                            ast_node.location.line, ast_node.location.column,
                            ast_node.kind, client_data.clang_parser.get_ast_node_name(ast_node)
                        )
                    )
                return ChildVisitResult.RECURSE.value  # If we are positioned in TU of interest, then we'll traverse through all descendants
            return ChildVisitResult.CONTINUE.value  # Otherwise, we'll skip to the next sibling

        # Build Vim syntax highlight rules
        start = time.clock()
        vim_syntax_element = ['call clearmatches()\n']
        if tunit:
            client_data = collections.namedtuple('client_data', ['clang_parser', 'vim_syntax_element'])
            clang_parser.traverse(tunit.cursor, client_data(clang_parser, vim_syntax_element), visitor)

        # Write Vim syntax file
        vim_syntax_file = open(self.output_syntax_file, "w", 0)
        vim_syntax_file.writelines(vim_syntax_element)
        time_elapsed = time.clock() - start

        # Apply newly generated syntax rules
        YavideUtils.call_vim_remote_function(self.yavide_instance, "Y_SrcCodeHighlighter_Apply('" + str(args[1]) + "'" + ", '" + self.output_syntax_file + "')")

        # Write some debug information
        clang_parser.dump_ast_nodes(tunit)

        # Log how long generating Vim syntax file took
        logging.info("Vim syntax generator for '{0}' took {1}.".format(str(args[1]), time_elapsed))

    def generate_vim_syntax_file_from_ctags(self, filename):
        # Generate the tags
        output_tag_file = "/tmp/yavide_tags"
        tokenizer = CtagsTokenizer(output_tag_file)
        tokenizer.run(filename)

        # Generate the vim syntax file
        tags_db = None
        try:
            tags_db = open(output_tag_file)
            # Build Vim syntax highlight rules
            vim_highlight_rules = set()
            for line in tags_db:
                if not tokenizer.is_header(line):
                    highlight_rule = VimSyntaxGenerator.__tag_id_to_vim_syntax_group(tokenizer.get_token_id(line)) + " " + tokenizer.get_token_name(line)
                    vim_highlight_rules.add(highlight_rule)

            vim_syntax_element = []
            for rule in vim_highlight_rules:
                vim_syntax_element.append("syntax keyword " + rule + "\n")

            # Write syntax file
            vim_syntax_file = open(self.output_syntax_file, "w")
            vim_syntax_file.writelines(vim_syntax_element)
        finally:
            if tags_db is not None:
                tags_db.close()

    @staticmethod
    def __tag_id_to_vim_syntax_group(tag_identifier):
        if tag_identifier == ASTNodeId.getNamespaceId():
            return "yavideCppNamespace"
        if tag_identifier == ASTNodeId.getNamespaceAliasId():
            return "yavideCppNamespaceAlias"
        if tag_identifier == ASTNodeId.getClassId():
            return "yavideCppClass"
        if tag_identifier == ASTNodeId.getStructId():
            return "yavideCppStructure"
        if tag_identifier == ASTNodeId.getEnumId():
            return "yavideCppEnum"
        if tag_identifier == ASTNodeId.getEnumValueId():
            return "yavideCppEnumValue"
        if tag_identifier == ASTNodeId.getUnionId():
            return "yavideCppUnion"
        if tag_identifier == ASTNodeId.getFieldId():
            return "yavideCppField"
        if tag_identifier == ASTNodeId.getLocalVariableId():
            return "yavideCppLocalVariable"
        if tag_identifier == ASTNodeId.getFunctionId():
            return "yavideCppFunction"
        if tag_identifier == ASTNodeId.getMethodId():
            return "yavideCppMethod"
        if tag_identifier == ASTNodeId.getFunctionParameterId():
            return "yavideCppFunctionParameter"
        if tag_identifier == ASTNodeId.getTemplateTypeParameterId():
            return "yavideCppTemplateTypeParameter"
        if tag_identifier == ASTNodeId.getTemplateNonTypeParameterId():
            return "yavideCppTemplateNonTypeParameter"
        if tag_identifier == ASTNodeId.getTemplateTemplateParameterId():
            return "yavideCppTemplateTemplateParameter"
        if tag_identifier == ASTNodeId.getMacroDefinitionId():
            return "yavideCppMacroDefinition"
        if tag_identifier == ASTNodeId.getMacroInstantiationId():
            return "yavideCppMacroInstantiation"
        if tag_identifier == ASTNodeId.getTypedefId():
            return "yavideCppTypedef"
        if tag_identifier == ASTNodeId.getUsingDirectiveId():
            return "yavideCppUsingDirective"
        if tag_identifier == ASTNodeId.getUsingDeclarationId():
            return "yavideCppUsingDeclaration"

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("filename",                                                       help="source code file to generate the source code highlighting for")
    parser.add_argument("output_syntax_file",                                             help="resulting Vim syntax file")
    args = parser.parse_args()
    args_dict = vars(args)

    vimHighlighter = VimSyntaxGenerator(args.output_syntax_file)
    vimHighlighter(args.filename, [''])

if __name__ == "__main__":
    main()

